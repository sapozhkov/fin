from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
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

    def get_delta_days_date(self, days: int, from_date: datetime | None = None) -> datetime:
        """
        Отдает дату за days дней до указанной (или текущей)
        ! в датах сохраняется текущее время
        """
        if from_date is None:
            from_date = self.now()
        return from_date - timedelta(days=days)


class TimeHelper(AbstractTimeHelper):
    def now(self):
        return datetime.now(timezone.utc)

    def sleep(self, seconds):
        time.sleep(seconds)
