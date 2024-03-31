from abc import ABC, abstractmethod
from datetime import datetime, timezone
import time


class AbstractTimeHelper(ABC):
    def __init__(self):
        self.tmz = 3

    @abstractmethod
    def now(self):
        pass

    def get_current_date(self) -> str:
        """отдает текущую дату в формате 'ГГГГ-ММ-ДД'"""
        return self.now().strftime('%Y-%m-%d')

    @abstractmethod
    def sleep(self, seconds):
        pass


class TimeHelper(AbstractTimeHelper):
    def now(self):
        return datetime.now(timezone.utc)

    def sleep(self, seconds):
        time.sleep(seconds)
