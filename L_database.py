"""
Supabase 데이터베이스와 연동하여 로또 데이터를 관리하고 업데이트하는 모듈입니다.
웹 스크래핑을 통해 최신 로또 당첨 번호를 가져와 데이터베이스에 저장합니다.
"""
import logging
import time
import threading
from typing import Optional, Tuple, List, Callable
import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client
from L_config import SUPABASE_URL, SUPABASE_KEY, BASE_URL

logger = logging.getLogger(__name__)

supabase: Optional[Client] = None

def init_supabase() -> Optional[Client]:
    """Supabase 클라이언트를 초기화하고 반환합니다."""
    global supabase
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            logger.info("Supabase 클라이언트 초기화 성공")
            return supabase
        except Exception as e:
            logger.error("Supabase 연결 오류: %s", e)
            return None
    logger.error("Supabase URL 또는 KEY가 설정되지 않았습니다.")
    return None

def load_lotto_data_from_supabase() -> Tuple[Optional[List[List[int]]], str]:
    """Supabase에서 로또 데이터 로드"""
    if not supabase:
        return None, "데이터베이스 연결이 설정되지 않았습니다."

    try:
        response = supabase.table('lotto_data').select(
            'num1, num2, num3, num4, num5, num6'
        ).order('round').execute()

        if response.data:
            winning_numbers = []
            for row in response.data:
                numbers = [row['num1'], row['num2'], row['num3'],
                           row['num4'], row['num5'], row['num6']]
                if all(1 <= x <= 45 for x in numbers) and len(set(numbers)) == 6:
                    winning_numbers.append(sorted(numbers))

            if winning_numbers:
                logger.info("데이터 로드 성공: %d개 당첨 번호", len(winning_numbers))
                return (winning_numbers,
                        f"데이터 로드 성공: 총 {len(winning_numbers)}개의 당첨 번호를 불러왔습니다.")

            logger.warning("유효한 데이터를 찾지 못함")
            return ([], "데이터베이스에서 유효한 데이터를 찾지 못했습니다.")

        logger.info("데이터베이스가 비어있음")
        return ([], "데이터베이스가 비어있습니다.")
    except Exception as e:
        logger.error("데이터베이스 조회 오류: %s", e)
        return None, f"데이터베이스 조회 중 오류 발생: {e}"

class DatabaseUpdater(threading.Thread):
    """로또 데이터를 업데이트하는 스레드 클래스"""
    def __init__(self, supabase_client: Client, on_progress: Callable[[str], None],
                 on_finished: Callable[[str], None]):
        super().__init__()
        self.supabase = supabase_client
        self.on_progress = on_progress
        self.on_finished = on_finished
        self.daemon = True # 메인 앱 종료 시 스레드도 함께 종료

    def run(self):
        try:
            self.on_progress("DB 최신 회차 확인 중...")
            response = self.supabase.table('lotto_data').select('round').order(
                'round', desc=True
            ).limit(1).execute()
            latest_local_round = response.data[0]['round'] if response.data else 0
            self.on_progress(f"DB 최신 회차: {latest_local_round}회")

            self.on_progress("웹 최신 회차 확인 중...")
            response = requests.get("https://www.dhlottery.co.kr/common.do?method=main",
                                    timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            latest_web_round = int(soup.select_one('#lottoDrwNo').text)
            self.on_progress(f"웹 최신 회차: {latest_web_round}회")

            if latest_local_round >= latest_web_round:
                self.on_finished(f"데이터가 최신입니다 ({latest_local_round}회)")
                return

            start_round = latest_local_round + 1
            new_data = []
            for round_num in range(start_round, latest_web_round + 1):
                self.on_progress(f"{round_num}회 데이터 수집 중...")
                win_nums, bonus_num = self._get_winning_numbers(round_num)
                if win_nums and bonus_num:
                    new_data.append({
                        'round': round_num, 'num1': win_nums[0], 'num2': win_nums[1],
                        'num3': win_nums[2], 'num4': win_nums[3], 'num5': win_nums[4],
                        'num6': win_nums[5], 'bonus': bonus_num
                    })
                time.sleep(0.2)

            if new_data:
                self.on_progress(f"{len(new_data)}개 데이터 저장 중...")
                self.supabase.table('lotto_data').upsert(new_data).execute()
                self.on_finished(f"업데이트 완료! ({len(new_data)}개 추가)")
            else:
                self.on_finished("업데이트 할 새로운 데이터가 없습니다.")

        except Exception as e:
            logger.error("업데이트 스레드 오류: %s", e)
            self.on_finished(f"업데이트 오류: {e}")

    def _get_winning_numbers(self, round_number: int) -> Tuple[Optional[List[int]], Optional[int]]:
        """특정 회차의 당첨 번호를 가져옵니다."""
        try:
            url = BASE_URL.format(round_number)
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            win_nums_spans = soup.select("div.win_result div.num.win p span.ball_645")
            bonus_num_span = soup.select_one("div.win_result div.num.bonus p span.ball_645")
            if len(win_nums_spans) == 6 and bonus_num_span:
                win_nums = [int(span.text) for span in win_nums_spans]
                bonus_num = int(bonus_num_span.text)
                return win_nums, bonus_num
            return None, None
        except Exception as e:
            logger.error("%d회 데이터 수집 오류: %s", round_number, e)
            return None, None