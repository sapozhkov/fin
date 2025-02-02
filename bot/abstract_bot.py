from abc import abstractmethod, ABC
from datetime import time as datetime_time
from typing import Tuple

from app.config import AccConfig, RunConfig
from app.helper import TimeHelper
from bot.env import AbstractTimeHelper, AbstractLoggerHelper


class AbstractBot(ABC):
    STATE_NEW = 1
    STATE_WORKING = 2
    STATE_FINISHED = 3

    # количество секунд задержки старта работы в начале торгового дня. хак, чтобы не влететь в отсечку утром
    START_SEC_SHIFT = 1

    def __init__(
            self,
            config: AccConfig | RunConfig,
            time_helper: AbstractTimeHelper | None = None,
            logger_helper: AbstractLoggerHelper | None = None,
    ):
        self.config = config
        self.time = time_helper
        self.logger = logger_helper

        self.state = self.STATE_NEW

    def is_trading_day(self):
        return TimeHelper.is_trading_day(self.time.now())

    def log(self, message, repeat=False):
        self.logger.log(message, repeat)

    def can_trade(self) -> Tuple[bool, int]:
        """
        Проверяет доступна ли торговля.
        Отдает статус "можно торговать" и количество секунд для задержки, если нет
        :return: (bool, int)
        """
        now = self.time.now()
        now_time = now.time()

        start_hour_str, start_min_str = self.config.start_time.split(':')
        end_hour_str, end_min_str = self.config.end_time.split(':')

        start_time = datetime_time(int(start_hour_str), int(start_min_str), self.START_SEC_SHIFT)
        end_time = datetime_time(int(end_hour_str), int(end_min_str))

        # ко времени запуска приближаемся шагами в половину оставшегося времени
        if now_time < start_time:
            now_sec = now_time.hour * 3600 + now_time.minute * 60 + now_time.second
            start_sec = start_time.hour * 3600 + start_time.minute * 60 + start_time.second
            delta_seconds = start_sec - now_sec
            return False, max(2, round(delta_seconds / 2))

        if now_time >= end_time:
            self.stop()
            return False, 0

        return True, 0

    def continue_trading(self):
        return self.state != self.STATE_FINISHED

    def run(self):
        while self.continue_trading():
            self.run_iteration()
        self.log('END')

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def run_iteration(self):
        pass

    @abstractmethod
    def stop(self, to_zero=False, exit_code=0):
        pass
