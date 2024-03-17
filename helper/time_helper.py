from abc import ABC, abstractmethod
from datetime import datetime, timezone
import time


class AbstractTimeHelper(ABC):
    def __init__(self):
        self.tmz = 3

    @abstractmethod
    def now(self):
        pass

    @abstractmethod
    def sleep(self, seconds):
        pass


class TimeHelper(AbstractTimeHelper):
    def now(self):
        return datetime.now(timezone.utc)
        # todo проверить норм ли будет - в коде было 2 варианта
        # market_tz = pytz.timezone('Europe/Moscow')
        # return datetime.now(market_tz)

    def sleep(self, seconds):
        time.sleep(seconds)
