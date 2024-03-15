from abc import ABC, abstractmethod
from datetime import datetime, timezone
import time


class AbstractTime(ABC):
    @abstractmethod
    def now(self):
        pass

    @abstractmethod
    def sleep(self, seconds):
        pass


class TimeHelper(AbstractTime):
    def __init__(self):
        pass

    def now(self):
        return datetime.now(timezone.utc)
        # todo проверить норм ли будет - в коде было 2 варианта
        # market_tz = pytz.timezone('Europe/Moscow')
        # return datetime.now(market_tz)

    def sleep(self, seconds):
        time.sleep(seconds)
