"""
로또 번호 생성 및 통계 분석 로직을 담당하는 모듈입니다.
과거 당첨 데이터를 기반으로 다양한 패턴의 로또 번호를 생성합니다.
"""
import random
from collections import Counter
from typing import List, Optional, Callable, Dict, Set, Tuple

class LottoLogic:
    """
    로또 번호 생성 및 통계 분석을 위한 클래스입니다.
    과거 당첨 번호를 분석하여 다양한 로또 번호 생성 전략을 제공합니다.
    """
    MIN_NUM: int = 1
    MAX_NUM: int = 45
    NUM_BALLS: int = 6

    def __init__(self, past_winnings: Optional[List[List[int]]] = None) -> None:
        self.past_winnings = past_winnings if past_winnings is not None else []
        self._patterns_analyzed = False

        # Initialize properties
        self.number_freq: Counter = Counter()
        self.hot_numbers: List[int] = []
        self.cold_numbers: List[int] = []
        self.pair_freq: Counter = Counter()
        self.incompatible_pairs: Set[Tuple[int, int]] = set()
        self.long_term_unseen: List[int] = []
        self.sum_stats: Dict[str, float] = {'min': 0, 'max': 0, 'avg': 0}

        if self.past_winnings:
            self._analyze_patterns()

    def _analyze_patterns(self) -> None:
        """과거 당첨 번호를 분석하여 통계 패턴을 업데이트합니다."""
        if self._patterns_analyzed:
            return

        if not self.past_winnings:
            return

        all_numbers_flat = [num for game in self.past_winnings for num in game]
        sums = [sum(game) for game in self.past_winnings]

        self.pair_freq.clear()
        for game in self.past_winnings:
            for i in range(self.NUM_BALLS):
                for j in range(i + 1, self.NUM_BALLS):
                    pair = tuple(sorted((game[i], game[j])))
                    self.pair_freq[pair] += 1

        if not all_numbers_flat:
            return

        self.number_freq = Counter(all_numbers_flat)
        total_freq = sum(self.number_freq.values())
        unique_numbers = len(self.number_freq)

        if unique_numbers > 0:
            avg_freq = total_freq / unique_numbers

            hot_items = [(n, f) for n, f in self.number_freq.items() if f > avg_freq]
            self.hot_numbers = [n for n, f in sorted(hot_items,
                                                     key=lambda x: x[1],
                                                     reverse=True)]

            all_numbers = set(range(self.MIN_NUM, self.MAX_NUM + 1))
            cold_numbers = [(n, self.number_freq.get(n, 0))
                            for n in all_numbers if self.number_freq.get(n, 0) < avg_freq]
            self.cold_numbers = [n for n, f in sorted(cold_numbers, key=lambda x: x[1])]

        self.incompatible_pairs = {p for p, f in self.pair_freq.items() if f <= 1}

        recent_limit = min(15, len(self.past_winnings))
        recent_numbers = set()
        for game in self.past_winnings[-recent_limit:]:
            recent_numbers.update(game)

        self.long_term_unseen = [n for n in range(self.MIN_NUM, self.MAX_NUM + 1)
                                 if n not in recent_numbers]

        if sums:
            self.sum_stats = {'min': min(sums), 'max': max(sums), 'avg': sum(sums) / len(sums)}

        self._patterns_analyzed = True

    def _generate_with_filter(self, condition: Callable[[List[int]], bool],
                              max_trials: int = 100) -> List[int]:
        """조건을 만족하는 숫자를 생성하는 헬퍼 함수."""
        for _ in range(max_trials):
            numbers = sorted(random.sample(range(self.MIN_NUM, self.MAX_NUM + 1),
                                           self.NUM_BALLS))
            if condition(numbers):
                return numbers
        return self.generate_random()

    def generate_random(self) -> List[int]:
        """무작위 로또 번호를 생성합니다."""
        return sorted(random.sample(range(self.MIN_NUM, self.MAX_NUM + 1),
                                    self.NUM_BALLS))

    def generate_pattern(self) -> List[int]:
        """과거 당첨 번호의 빈도를 기반으로 로또 번호를 생성합니다."""
        if not self.past_winnings:
            return self.generate_random()
        population = list(self.number_freq.keys())
        weights = list(self.number_freq.values())
        if not population:
            return self.generate_random()

        numbers = set()
        max_attempts = 100
        attempt = 0
        while len(numbers) < self.NUM_BALLS and attempt < max_attempts:
            numbers.add(random.choices(population, weights=weights, k=1)[0])
            attempt += 1
        return sorted(list(numbers))

    def generate_inverse_pattern(self) -> List[int]:
        """과거 당첨 번호의 낮은 빈도를 기반으로 로또 번호를 생성합니다."""
        if not self.past_winnings:
            return self.generate_random()
        all_possible_nums = list(range(self.MIN_NUM, self.MAX_NUM + 1))
        max_f = max(self.number_freq.values()) if self.number_freq else 0
        weights = [(max_f - self.number_freq.get(num, 0)) + 1
                   for num in all_possible_nums]

        numbers = set()
        max_attempts = 100
        attempt = 0
        while len(numbers) < self.NUM_BALLS and attempt < max_attempts:
            numbers.add(random.choices(all_possible_nums, weights=weights, k=1)[0])
            attempt += 1
        return sorted(list(numbers))

    def generate_balance(self) -> List[int]:
        """홀짝 비율이 균형 잡힌 로또 번호를 생성합니다 (2~4개 짝수)."""
        return self._generate_with_filter(lambda n: 2 <= sum(1 for x in n if x % 2 == 0) <= 4)

    def generate_range_distribution(self) -> List[int]:
        """번호대별 균형을 맞춘 로또 번호를 생성합니다."""
        try:
            n = set()
            ranges = [(1, 15), (16, 30), (31, 45)]
            for s, e in ranges:
                n.update(random.sample(range(s, e + 1), 2))
            while len(n) < self.NUM_BALLS:
                n.add(random.randint(self.MIN_NUM, self.MAX_NUM))
            sample_size = min(self.NUM_BALLS, len(n))
            return sorted(random.sample(list(n), sample_size))
        except (ValueError, IndexError):
            return self.generate_random()

    def generate_prime(self) -> List[int]:
        """소수를 포함하는 로또 번호를 생성합니다 (최소 2개 소수)."""
        primes = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43}
        return self._generate_with_filter(lambda n: sum(1 for x in n if x in primes) >= 2)

    def generate_sum_range(self, min_sum: Optional[int] = None,
                           max_sum: Optional[int] = None) -> List[int]:
        """합계 범위 내의 로또 번호를 생성합니다."""
        min_s = min_sum or (self.sum_stats['min'] if self.past_winnings else 111)
        max_s = max_sum or (self.sum_stats['max'] if self.past_winnings else 170)
        return self._generate_with_filter(lambda n: min_s <= sum(n) <= max_s)

    def generate_consecutive(self) -> List[int]:
        """연속된 숫자를 포함하는 로또 번호를 생성합니다."""
        def has_consecutive(n: List[int]) -> bool:
            for i in range(len(n) - 1):
                if n[i+1] == n[i] + 1:
                    return True
            return False
        return self._generate_with_filter(has_consecutive)

    def generate_hot_cold_mix(self) -> List[int]:
        """핫 넘버와 콜드 넘버를 혼합하여 로또 번호를 생성합니다."""
        if not self.past_winnings:
            return self.generate_random()

        n = set()
        if self.hot_numbers:
            n.update(random.sample(self.hot_numbers, min(3, len(self.hot_numbers))))
        if self.cold_numbers:
            n.update(random.sample(self.cold_numbers, min(3, len(self.cold_numbers))))

        while len(n) < self.NUM_BALLS:
            n.add(random.randint(self.MIN_NUM, self.MAX_NUM))
        sample_size = min(self.NUM_BALLS, len(n))
        return sorted(random.sample(list(n), sample_size))

    def generate_frequent_pairs(self) -> List[int]:
        """자주 등장하는 쌍을 포함하는 로또 번호를 생성합니다."""
        if not self.pair_freq:
            return self.generate_random()

        top_pairs = self.pair_freq.most_common(10)
        if not top_pairs:
            return self.generate_random()

        n = set(random.choice(top_pairs)[0])
        while len(n) < self.NUM_BALLS:
            n.add(random.randint(self.MIN_NUM, self.MAX_NUM))
        sample_size = min(self.NUM_BALLS, len(n))
        return sorted(random.sample(list(n), sample_size))

    def generate_ending_pattern(self) -> List[int]:
        """끝자리 패턴을 고려하여 로또 번호를 생성합니다."""
        groups = {i: [n for n in range(self.MIN_NUM, self.MAX_NUM + 1)
                      if n % 10 == i] for i in range(10)}
        n = set()
        for _ in range(random.randint(1, 3)):
            chosen_ending = random.choice(list(groups.keys()))
            if groups[chosen_ending]:
                n.add(random.choice(groups[chosen_ending]))

        while len(n) < self.NUM_BALLS:
            n.add(random.randint(self.MIN_NUM, self.MAX_NUM))
        sample_size = min(self.NUM_BALLS, len(n))
        return sorted(random.sample(list(n), sample_size))

    def generate_statistical_optimal(self) -> List[int]:
        """통계적으로 최적화된 로또 번호를 생성합니다."""
        if not self.past_winnings:
            return self.generate_random()

        min_s, max_s = self.sum_stats['min'], self.sum_stats['max']

        def is_optimal(n: List[int]) -> bool:
            s = sum(n)
            even_count = sum(1 for x in n if x % 2 == 0)
            return (2 <= even_count <= 4) and (min_s <= s <= max_s)

        return self._generate_with_filter(is_optimal, max_trials=200)

    def generate_carryover_unseen_mix(self) -> List[int]:
        """이월 번호와 장기 미출현 번호를 혼합하여 로또 번호를 생성합니다."""
        if len(self.past_winnings) < 15:
            return self.generate_random()

        n = set(random.sample(self.past_winnings[-1], random.randint(1, 2)))
        if self.long_term_unseen:
            n.update(random.sample(self.long_term_unseen, random.randint(2, 3)))

        while len(n) < self.NUM_BALLS:
            n.add(random.randint(self.MIN_NUM, self.MAX_NUM))
        sample_size = min(self.NUM_BALLS, len(n))
        return sorted(random.sample(list(n), sample_size))

    def generate_same_ending_mix(self) -> List[int]:
        """동일한 끝자리를 포함하는 로또 번호를 생성합니다."""
        groups = {i: [n for n in range(self.MIN_NUM, self.MAX_NUM + 1)
                      if n % 10 == i] for i in range(10)}
        endings_with_pairs = [i for i, g in groups.items() if len(g) >= 2]
        if not endings_with_pairs:
            return self.generate_random()

        chosen_ending = random.choice(endings_with_pairs)
        n = set(random.sample(groups[chosen_ending], 2))

        while len(n) < self.NUM_BALLS:
            n.add(random.randint(self.MIN_NUM, self.MAX_NUM))
        return sorted(list(n))

    def generate_compatibility_mix(self) -> List[int]:
        """비호환 쌍을 피하여 로또 번호를 생성합니다."""
        if not self.incompatible_pairs:
            return self.generate_random()

        def is_compatible(n: List[int]) -> bool:
            for i in range(self.NUM_BALLS):
                for j in range(i + 1, self.NUM_BALLS):
                    if tuple(sorted((n[i], n[j]))) in self.incompatible_pairs:
                        return False
            return True

        return self._generate_with_filter(is_compatible, max_trials=200)

    def _get_generation_methods(self, data_driven_only: bool = False,
                                all_methods: bool = False) -> List[Callable[[], List[int]]]:
        """생성 메서드 목록을 반환하는 헬퍼 함수."""
        all_method_map = [
            (self.generate_random, False),
            (self.generate_pattern, True),
            (self.generate_inverse_pattern, True),
            (self.generate_balance, False),
            (self.generate_range_distribution, False),
            (self.generate_prime, False),
            (self.generate_sum_range, True),
            (self.generate_consecutive, False),
            (self.generate_hot_cold_mix, True),
            (self.generate_frequent_pairs, True),
            (self.generate_ending_pattern, False),
            (self.generate_statistical_optimal, True),
            (self.generate_carryover_unseen_mix, True),
            (self.generate_same_ending_mix, False),
            (self.generate_compatibility_mix, True),
        ]

        if data_driven_only:
            return [m for m, is_data_dep in all_method_map if is_data_dep]
        if all_methods:
            return [m for m, _ in all_method_map]
        return [m for m, _ in all_method_map]


    def generate_data_driven_mix(self) -> List[int]:
        """데이터 기반 생성 메서드들을 혼합하여 로또 번호를 생성합니다."""
        if not self.past_winnings:
            return self.generate_random()

        methods = self._get_generation_methods(data_driven_only=True)
        all_n = set()
        for method in methods:
            try:
                all_n.update(method())
            except Exception:
                continue

        while len(all_n) < self.NUM_BALLS:
            all_n.add(random.randint(self.MIN_NUM, self.MAX_NUM))
        sample_size = min(self.NUM_BALLS, len(all_n))
        return sorted(random.sample(list(all_n), sample_size))

    def generate_all_methods(self) -> List[int]:
        """모든 생성 메서드들을 혼합하여 로또 번호를 생성합니다."""
        methods = self._get_generation_methods(all_methods=True)
        all_n = set()

        for method in methods:
            try:
                all_n.update(method())
            except Exception:
                continue

        while len(all_n) < self.NUM_BALLS:
            all_n.add(random.randint(self.MIN_NUM, self.MAX_NUM))
        sample_size = min(self.NUM_BALLS, len(all_n))
        return sorted(random.sample(list(all_n), sample_size))