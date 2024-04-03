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

    @staticmethod
    def get_remaining_time_text(remaining_time):
        # Преобразуем секунды в часы, минуты и секунды
        hours, remainder = divmod(remaining_time, 3600)
        minutes, seconds = divmod(remainder, 60)

        # Формируем строку для вывода с учетом наличия часов
        parts = []
        if hours > 0:
            parts.append(f"{int(hours):02}h")
        if minutes > 0 or hours > 0:  # Выводим минуты, если есть часы или минуты
            parts.append(f"{int(minutes):02}m")
        parts.append(f"{int(seconds):02}s")

        return " ".join(parts[:2])


class TimeHelper(AbstractTimeHelper):
    def now(self):
        return datetime.now(timezone.utc)

    def sleep(self, seconds):
        time.sleep(seconds)
