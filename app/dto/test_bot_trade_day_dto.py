from dataclasses import dataclass


@dataclass
class TestBotTradeDayDto:
    operations: int = 0
    end_price: float = 0.0
    end_cnt: int = 0
    start_price: float = 0.0
    start_cnt: int = 0
    day_sum: float = 0.0
