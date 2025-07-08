import json
import csv
import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import os

from L_config import SUPABASE_URL, SUPABASE_KEY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LottoDataManager:
    def __init__(self, data_file: str = "lotto_data.json"):
        self.data_file = data_file
        self.csv_file = data_file.replace('.json', '.csv')
        self.supabase_headers = {
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
            'Content-Type': 'application/json'
        }
        
    def download_from_supabase(self) -> List[Dict]:
        """Supabase에서 모든 로또 데이터를 다운로드"""
        try:
            url = f"{SUPABASE_URL}/rest/v1/lotto_data"
            params = {
                'select': 'round,num1,num2,num3,num4,num5,num6,bonus,draw_date',
                'order': 'round.asc'
            }
            
            response = requests.get(url, headers=self.supabase_headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Supabase에서 {len(data)}개 회차 데이터 다운로드 완료")
            return data
            
        except Exception as e:
            logger.error(f"Supabase 데이터 다운로드 실패: {e}")
            return []
    
    def scrape_latest_round_from_web(self) -> Optional[Dict]:
        """웹에서 최신 회차 정보 스크래핑"""
        try:
            # 동행복권 최신 회차 확인
            url = "https://www.dhlottery.co.kr/gameResult.do?method=byWin"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
                'Connection': 'keep-alive'
            }
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 회차 정보 추출
            round_elem = soup.find('strong', id='lottoDrwNo')
            if not round_elem:
                return None
                
            round_num = int(round_elem.text.strip())
            
            # 당첨번호 추출
            ball_elems = soup.find_all('span', class_='ball_645')
            if len(ball_elems) < 7:
                return None
                
            numbers = [int(elem.text) for elem in ball_elems[:6]]
            bonus = int(ball_elems[6].text)
            
            # 추첨일 추출
            date_elem = soup.find('p', class_='desc')
            draw_date = None
            if date_elem:
                date_text = date_elem.text
                import re
                date_match = re.search(r'(\d{4})\.\d{2}\.\d{2}', date_text)
                if date_match:
                    draw_date = date_text.split('(')[0].strip()
            
            result = {
                'round': round_num,
                'num1': numbers[0], 'num2': numbers[1], 'num3': numbers[2],
                'num4': numbers[3], 'num5': numbers[4], 'num6': numbers[5],
                'bonus': bonus,
                'draw_date': draw_date or datetime.now().strftime('%Y.%m.%d')
            }
            
            logger.info(f"웹에서 최신 회차 {round_num} 정보 스크래핑 완료")
            return result
            
        except Exception as e:
            logger.error(f"웹 스크래핑 실패: {e}")
            return None
    
    def load_local_data(self) -> List[Dict]:
        """로컬 JSON 파일에서 데이터 로드"""
        if not os.path.exists(self.data_file):
            return []
            
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"로컬에서 {len(data)}개 회차 데이터 로드")
            return data
        except Exception as e:
            logger.error(f"로컬 데이터 로드 실패: {e}")
            return []
    
    def save_local_data(self, data: List[Dict]) -> bool:
        """데이터를 로컬 JSON 및 CSV 파일로 저장"""
        try:
            # JSON 저장
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # CSV 저장 (APK 포함용)
            if data:
                with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
            
            logger.info(f"{len(data)}개 회차 데이터를 {self.data_file}와 {self.csv_file}에 저장")
            return True
            
        except Exception as e:
            logger.error(f"데이터 저장 실패: {e}")
            return False
    
    def get_latest_round(self, data: List[Dict]) -> int:
        """데이터에서 최신 회차 번호 반환"""
        if not data:
            return 0
        return max(item['round'] for item in data)
    
    def update_data_file(self) -> Tuple[bool, str]:
        """데이터 파일 업데이트 (웹에서 최신 정보 확인하여 추가)"""
        local_data = self.load_local_data()
        latest_local_round = self.get_latest_round(local_data)
        
        # 웹에서 최신 회차 확인
        latest_web_data = self.scrape_latest_round_from_web()
        if not latest_web_data:
            return False, "웹에서 최신 정보를 가져올 수 없습니다"
            
        latest_web_round = latest_web_data['round']
        
        if latest_web_round <= latest_local_round:
            return True, f"이미 최신 데이터입니다 (로컬: {latest_local_round}회, 웹: {latest_web_round}회)"
        
        # 누락된 회차들을 위해 supabase에서 추가 데이터 가져오기
        missing_rounds = list(range(latest_local_round + 1, latest_web_round + 1))
        logger.info(f"누락된 회차: {missing_rounds}")
        
        # Supabase에서 누락된 데이터 가져오기
        updated_data = local_data.copy()
        
        for round_num in missing_rounds:
            if round_num == latest_web_round:
                # 최신 회차는 웹에서 가져온 데이터 사용
                updated_data.append(latest_web_data)
            else:
                # 이전 회차들은 supabase에서 가져오기
                try:
                    url = f"{SUPABASE_URL}/rest/v1/lotto_data"
                    params = {
                        'select': 'round,num1,num2,num3,num4,num5,num6,bonus,draw_date',
                        'round': f'eq.{round_num}'
                    }
                    
                    response = requests.get(url, headers=self.supabase_headers, params=params)
                    if response.status_code == 200:
                        round_data = response.json()
                        if round_data:
                            updated_data.extend(round_data)
                            
                except Exception as e:
                    logger.warning(f"{round_num}회차 데이터 가져오기 실패: {e}")
        
        # 회차별로 정렬
        updated_data.sort(key=lambda x: x['round'])
        
        # 저장
        if self.save_local_data(updated_data):
            return True, f"데이터 업데이트 완료 ({len(missing_rounds)}개 회차 추가)"
        else:
            return False, "데이터 저장 실패"
    
    def create_initial_data_file(self) -> Tuple[bool, str]:
        """초기 데이터 파일 생성 (Supabase에서 모든 데이터 다운로드)"""
        data = self.download_from_supabase()
        if not data:
            return False, "Supabase에서 데이터를 가져올 수 없습니다"
        
        if self.save_local_data(data):
            return True, f"초기 데이터 파일 생성 완료 ({len(data)}개 회차)"
        else:
            return False, "데이터 저장 실패"

def main():
    """메인 실행 함수"""
    manager = LottoDataManager()
    
    print("=== 로또 데이터 관리자 ===")
    print("1. 초기 데이터 파일 생성 (Supabase에서 모든 데이터 다운로드)")
    print("2. 데이터 파일 업데이트 (웹에서 최신 정보 확인)")
    print("3. 현재 데이터 파일 정보 확인")
    
    choice = input("선택하세요 (1-3): ").strip()
    
    if choice == "1":
        print("Supabase에서 모든 데이터를 다운로드합니다...")
        success, message = manager.create_initial_data_file()
        print(f"결과: {message}")
        
    elif choice == "2":
        print("데이터 파일을 업데이트합니다...")
        success, message = manager.update_data_file()
        print(f"결과: {message}")
        
    elif choice == "3":
        data = manager.load_local_data()
        if data:
            latest_round = manager.get_latest_round(data)
            print(f"현재 데이터: {len(data)}개 회차 (최신: {latest_round}회)")
        else:
            print("데이터 파일이 없거나 비어있습니다.")
    
    else:
        print("잘못된 선택입니다.")

if __name__ == "__main__":
    main()