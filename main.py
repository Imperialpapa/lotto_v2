import os
import platform
from kivy.config import Config

# OS별 폰트 경로 자동 설정
def setup_fonts():
    system = platform.system().lower()
    
    if system == 'windows':
        # Windows
        font_paths = [
            'c:/Windows/Fonts/malgun.ttf',
            'c:/Windows/Fonts/malgunbd.ttf',
            'c:/Windows/Fonts/gulim.ttc',
            'c:/Windows/Fonts/arial.ttf'
        ]
    elif system == 'darwin':
        # macOS
        font_paths = [
            '/System/Library/Fonts/AppleSDGothicNeo.ttc',
            '/Library/Fonts/Arial.ttf',
            '/System/Library/Fonts/Helvetica.ttc'
        ]
    elif system == 'linux':
        # Linux/WSL
        font_paths = [
            '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
            '/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf',
            '/usr/share/fonts/truetype/nanum/NanumSquare.ttf',
            '/usr/share/fonts/TTF/NanumGothic.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
        ]
    else:
        # 안드로이드/기타 모바일
        font_paths = [
            '/system/fonts/NotoSansCJK-Regular.ttc',
            '/system/fonts/DroidSans.ttf',
            '/system/fonts/Roboto-Regular.ttf'
        ]
    
    # 존재하는 첫 번째 폰트 사용
    font_found = False
    selected_font = None
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                # 더 강력한 폰트 설정
                Config.set('kivy', 'default_font', [
                    'DefaultFont', font_path, font_path, font_path, font_path
                ])
                selected_font = font_path
                print(f"한글 폰트 설정 완료: {font_path}")
                font_found = True
                break
            except Exception as e:
                print(f"폰트 설정 실패: {font_path} - {e}")
                continue
    
    if not font_found:
        print("한글 폰트를 찾을 수 없습니다.")
        print("다음 명령어로 한글 폰트를 설치해 주세요:")
        print("sudo apt install fonts-nanum fonts-nanum-coding")
        # 기본 fallback 폰트라도 설정
        try:
            Config.set('kivy', 'default_font', ['Roboto', 'data/fonts/Roboto-Regular.ttf'])
        except:
            pass
    
    return selected_font

selected_font = setup_fonts()

# 모바일/데스크톱 해상도 설정 (setup_fonts 후에 실행)
system = platform.system().lower()
if system in ['linux', 'darwin', 'windows']:
    Config.set('graphics', 'width', '400')
    Config.set('graphics', 'height', '700')

import kivy
kivy.require('2.1.0')

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ListProperty
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.core.text import DEFAULT_FONT
import logging
from lotto_dataman import LottoDataManager

from L_lotto_logic import LottoLogic
from L_database_local import init_local_database, load_lotto_data_from_local, LocalDatabaseUpdater

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LottoBall(Widget):
    number = NumericProperty(0)
    ball_color = ListProperty([0.2, 0.2, 0.2, 1])

    def on_number(self, instance, value):
        self.ball_color = self.get_color_for_number(value)

    def get_color_for_number(self, number: int) -> list:
        if 1 <= number <= 10: return [0.98, 0.77, 0, 1]
        if 11 <= number <= 20: return [0.41, 0.78, 0.95, 1]
        if 21 <= number <= 30: return [1, 0.45, 0.45, 1]
        if 31 <= number <= 40: return [0.67, 0.67, 0.67, 1]
        if 41 <= number <= 45: return [0.69, 0.85, 0.25, 1]
        return [0.2, 0.2, 0.2, 1]

class LottoAnimationWidget(FloatLayout):
    def start_animation(self, numbers, callback):
        self.clear_widgets()
        max_delay = 0
        ball_size = min(self.width * 0.12, 45)  # 모바일 화면에 맞는 크기 조정
        
        for i, num in enumerate(numbers):
            ball = LottoBall(number=num)
            ball.size_hint = (None, None)
            ball.size = (ball_size, ball_size)
            ball.center_x = self.width / 2
            ball.center_y = self.height / 2
            ball.opacity = 0
            self.add_widget(ball)

            delay = i * 0.25  # 약간 더 빠른 애니메이션
            # 모바일 화면에 맞는 위치 조정
            target_x = self.width * 0.1 + i * (self.width * 0.13)
            anim = Animation(
                center_x=target_x,
                center_y=self.height / 2,
                opacity=1,
                t='out_bounce',
                duration=1.2
            )
            Clock.schedule_once(lambda dt, b=ball, a=anim: a.start(b), delay)
            max_delay = delay + 1.2

        Clock.schedule_once(callback, max_delay + 0.3)

class QueryResultsPopup(Popup):
    def __init__(self, data, **kwargs):
        super().__init__(**kwargs)
        self.title = f"당첨번호 ({len(data)}개)"
        results_layout = self.ids.query_results_layout
        results_layout.clear_widgets()
        
        for row in data:
            # 모바일 친화적인 조회 결과 레이아웃
            round_layout = BoxLayout(
                spacing=6, 
                size_hint_y=None, 
                height='50dp',
                padding='6dp'
            )
            
            # 회차 표시를 더 컴팩트하게
            round_label = Label(
                text=f"{row['round']}회", 
                size_hint_x=0.2, 
                font_size='12sp',
                color=[0.4, 0.4, 0.4, 1]
            )
            round_layout.add_widget(round_label)
            
            # 볼들을 더 작게 배치
            balls_layout = BoxLayout(spacing=2)
            numbers = [row['num1'], row['num2'], row['num3'], row['num4'], row['num5'], row['num6']]
            for number in numbers:
                ball = LottoBall(number=number)
                balls_layout.add_widget(ball)
            
            round_layout.add_widget(balls_layout)
            
            # 카드 스타일 배경 - bind를 사용하여 크기 변경 시 업데이트
            def update_round_background(instance, *args):
                instance.canvas.before.clear()
                with instance.canvas.before:
                    from kivy.graphics import Color, RoundedRectangle
                    Color(0.98, 0.98, 0.98, 1)
                    RoundedRectangle(pos=instance.pos, size=instance.size, radius=[4])
            
            round_layout.bind(pos=update_round_background, size=update_round_background)
            update_round_background(round_layout)
            
            results_layout.add_widget(round_layout)

class LottoGeneratorLayout(BoxLayout):
    def initialize_app(self):
        self.logic = LottoLogic()
        self.past_winnings = []
        self.local_db_connected = False
        self.local_db = None
        self.generated_numbers_cache = []
        self.populate_methods()
        self.init_local_database_connection()

    def init_local_database_connection(self):
        self.local_db = init_local_database()
        if self.local_db:
            self.local_db_connected = True
            self.ids.db_status_label.text = "데이터 로드 완료"
            self.load_data_from_local_database()
            self.update_default_round_values()
            self.check_for_updates()
        else:
            self.ids.db_status_label.text = "데이터 로드 실패"

    def load_data_from_local_database(self):
        if not self.local_db_connected or hasattr(self, '_data_loaded'): 
            return
        self.past_winnings, msg = load_lotto_data_from_local()
        self.past_winnings = self.past_winnings or []
        self.logic = LottoLogic(self.past_winnings)
        self.update_method_spinner()
        self._data_loaded = True

    def update_default_round_values(self):
        """최신 회차를 기준으로 조회 기본값 설정 (최신-4회 ~ 최신회)"""
        if not self.local_db_connected:
            return
        
        try:
            # 최신 회차 가져오기
            latest_round = self.local_db.get_latest_round()
            
            if latest_round is not None:
                from_round = max(1, latest_round - 4)  # 최신-4회 (최소 1회)
                to_round = latest_round
                
                # UI 기본값 설정
                self.ids.from_round_input.text = str(from_round)
                self.ids.to_round_input.text = str(to_round)
                
                logger.info(f"조회 기본값 설정: {from_round}회 ~ {to_round}회")
            else:
                # 기본값으로 설정
                self.ids.from_round_input.text = "1120"
                self.ids.to_round_input.text = "1125"
                
        except Exception as e:
            logger.error(f"기본 회차값 설정 오류: {e}")
            # 오류 시 기본값 사용
            self.ids.from_round_input.text = "1120"
            self.ids.to_round_input.text = "1125"

    def populate_methods(self):
        self.method_definitions = [
            {'name': "1. 기본 랜덤", 'method': self.logic.generate_random, 'data_dependent': False},
            {'name': "2. 패턴 분석 (자주)", 'method': self.logic.generate_pattern, 'data_dependent': True},
            {'name': "3. 패턴 분석 (드물게)", 'method': self.logic.generate_inverse_pattern, 'data_dependent': True},
            {'name': "4. 홀수/짝수 균형", 'method': self.logic.generate_balance, 'data_dependent': False},
            {'name': "5. 숫자 범위 분포", 'method': self.logic.generate_range_distribution, 'data_dependent': False},
            {'name': "6. 소수 번호 포함", 'method': self.logic.generate_prime, 'data_dependent': False},
            {'name': "7. 번호 총합 기반", 'method': self.logic.generate_sum_range, 'data_dependent': True},
            {'name': "8. 연속 번호 포함", 'method': self.logic.generate_consecutive, 'data_dependent': False},
            {'name': "9. 핫/콜드 번호 조합", 'method': self.logic.generate_hot_cold_mix, 'data_dependent': True},
            {'name': "10. 자주 나온 번호 쌍 기반", 'method': self.logic.generate_frequent_pairs, 'data_dependent': True},
            {'name': "11. 끝자리 패턴 분석", 'method': self.logic.generate_ending_pattern, 'data_dependent': True},
            {'name': "12. 통계적 최적화", 'method': self.logic.generate_statistical_optimal, 'data_dependent': True},
            {'name': "13. 이월수/미출현수 조합", 'method': self.logic.generate_carryover_unseen_mix, 'data_dependent': True},
            {'name': "14. 동일 끝수 조합", 'method': self.logic.generate_same_ending_mix, 'data_dependent': True},
            {'name': "15. 궁합수 분석(상극 제외)", 'method': self.logic.generate_compatibility_mix, 'data_dependent': True},
            {'name': "16. 데이터 기반 조합", 'method': self.logic.generate_data_driven_mix, 'data_dependent': True},
            {'name': "17. 모든 방법 조합", 'method': self.logic.generate_all_methods, 'data_dependent': True}
        ]
        self.update_method_spinner()

    def update_method_spinner(self):
        spinner = self.ids.method_spinner
        spinner.values = [m['name'] for m in self.method_definitions if not m['data_dependent'] or self.past_winnings]
        if spinner.text not in spinner.values: spinner.text = "1. 기본 랜덤"

    def generate_numbers(self):
        self.clear_results(switch_screen=False)
        
        method_name = self.ids.method_spinner.text
        selected_method = next((m for m in self.method_definitions if m['name'] == method_name), self.method_definitions[0])
        
        try: num_games = int(self.ids.games_input.text)
        except ValueError: num_games = 5

        self.generated_numbers_cache = []
        for _ in range(num_games):
            try: numbers = selected_method['method']()
            except Exception as e: numbers = self.logic.generate_random()
            self.generated_numbers_cache.append(numbers)

        if not self.generated_numbers_cache: return

        self.ids.screen_manager.current = 'animation_screen'
        first_game_numbers = self.generated_numbers_cache[0]
        self.ids.animation_widget.start_animation(first_game_numbers, self.show_results_after_animation)

    def show_results_after_animation(self, dt):
        for i, numbers in enumerate(self.generated_numbers_cache):
            self.add_game_to_results(i + 1, numbers)
        self.ids.screen_manager.current = 'results_screen'

    def add_game_to_results(self, game_num, numbers):
        # 모바일 친화적인 결과 레이아웃
        game_layout = BoxLayout(
            spacing=8, 
            size_hint_y=None, 
            height='55dp',
            padding='8dp'
        )
        
        # 게임 번호를 더 작게 표시
        game_label = Label(
            text=f"#{game_num}", 
            size_hint_x=0.15, 
            font_size='12sp',
            color=[0.6, 0.6, 0.6, 1]
        )
        game_layout.add_widget(game_label)
        
        # 볼들을 더 컴팩트하게 배치
        balls_layout = BoxLayout(spacing=3)
        for number in numbers: 
            ball = LottoBall(number=number)
            balls_layout.add_widget(ball)
        game_layout.add_widget(balls_layout)
        
        # 카드 스타일 배경 추가 - bind를 사용하여 크기 변경 시 업데이트
        def update_background(instance, *args):
            instance.canvas.before.clear()
            with instance.canvas.before:
                from kivy.graphics import Color, RoundedRectangle
                Color(0.95, 0.95, 0.95, 1)
                RoundedRectangle(pos=instance.pos, size=instance.size, radius=[4])
        
        game_layout.bind(pos=update_background, size=update_background)
        update_background(game_layout)
        
        self.ids.results_layout.add_widget(game_layout)

    def clear_results(self, switch_screen=True):
        self.ids.results_layout.clear_widgets()
        self.ids.animation_widget.clear_widgets()
        if switch_screen: self.ids.screen_manager.current = 'animation_screen'

    def query_winning_numbers(self):
        if not self.local_db_connected:
            popup = Popup(title='오류', content=Label(text='데이터를 로드할 수 없습니다.'), size_hint=(0.8, 0.4))
            popup.open()
            return

        try:
            from_round = int(self.ids.from_round_input.text)
            to_round = int(self.ids.to_round_input.text)
        except ValueError:
            popup = Popup(title='입력 오류', content=Label(text='회차는 숫자로 입력해야 합니다.'), size_hint=(0.8, 0.4))
            popup.open()
            return

        if from_round > to_round:
            popup = Popup(title='입력 오류', content=Label(text='시작 회차가 끝 회차보다 클 수 없습니다.'), size_hint=(0.8, 0.4))
            popup.open()
            return

        try:
            data = self.local_db.query_data_by_range(from_round, to_round)
            
            if not data:
                popup = Popup(title='조회 결과 없음', content=Label(text=f'{from_round}~{to_round}회차 데이터가 없습니다.'), size_hint=(0.8, 0.4))
                popup.open()
                return

            popup = QueryResultsPopup(data=data)
            popup.open()

        except Exception as e:
            logger.error(f"당첨번호 조회 오류: {e}")
            popup = Popup(title='조회 오류', content=Label(text=f'오류가 발생했습니다: {e}'), size_hint=(0.8, 0.4))
            popup.open()

    def check_for_updates(self):
        """동행복권 웹사이트에서 최신 데이터 확인"""
        if not self.local_db_connected:
            return
        
        self.ids.db_status_label.text = "최신 데이터 확인 중..."
        
        # 별도 스레드에서 업데이트 확인
        Clock.schedule_once(self._check_updates_async, 0.1)
    
    def _check_updates_async(self, dt):
        """비동기로 업데이트 확인"""
        try:
            updater = LocalDatabaseUpdater(database_instance=self.local_db)
            needs_update, message = updater.start()
            
            if needs_update:
                self.ids.db_status_label.text = f"새로운 데이터 발견: {message} (자동 업데이트 시작)"
                self.perform_update() # 자동 업데이트 시작
            else:
                self.ids.db_status_label.text = f"최신 상태: {message}"
                
        except Exception as e:
            logger.warning(f"업데이트 확인 실패: {e}")
            self.ids.db_status_label.text = "데이터 로드 완료 (업데이트 확인 실패)"
    
    
    
    def perform_update(self):
        """실제 업데이트 수행"""
        if hasattr(self, 'update_popup'):
            self.update_popup.dismiss()
        
        self.ids.db_status_label.text = "데이터 업데이트 중..."
        
        # lotto_dataman을 사용하여 업데이트
        Clock.schedule_once(self._perform_update_async, 0.1)
    
    def _perform_update_async(self, dt):
        """비동기로 업데이트 수행"""
        try:
            manager = LottoDataManager()
            success, message = manager.update_data_file()
            
            if success:
                self.ids.db_status_label.text = f"업데이트 완료: {message}"
                # 데이터 다시 로드
                self._data_loaded = False
                self.load_data_from_local_database()
                self.update_default_round_values()
            else:
                self.ids.db_status_label.text = f"업데이트 실패: {message}"
                
        except Exception as e:
            logger.error(f"데이터 업데이트 실패: {e}")
            self.ids.db_status_label.text = "업데이트 실패"

# Kivy 레이아웃 파일은 LottoApp에서 자동 로드됨

class LottoApp(App):
    def build(self):
        return LottoGeneratorLayout()

    def on_start(self):
        # 앱 시작 후 폰트 재설정 (더 확실한 방법)
        if selected_font:
            try:
                from kivy.core.text import LabelBase
                LabelBase.register(DEFAULT_FONT, selected_font)
                print(f"앱 시작 후 폰트 재설정: {selected_font}")
            except Exception as e:
                print(f"앱 시작 후 폰트 설정 실패: {e}")
        
        self.root.initialize_app()

if __name__ == '__main__':
    LottoApp().run()