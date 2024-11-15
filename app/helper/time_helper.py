from datetime import datetime, timezone, time, timedelta

from .day_exclusions import DayExclusions


class TimeHelper:
    DATE_FORMAT = "%Y-%m-%d"

    # todo #148 вот это тоже поменять или так и применять в этом виде
    START_TIME = '07:00'
    END_TIME = '15:29'

    @classmethod
    def now(cls) -> datetime:
        return datetime.now(timezone.utc)

    @classmethod
    def is_today(cls, date: str) -> bool:
        return date == cls.now().strftime(cls.DATE_FORMAT)

    @classmethod
    def is_evening(cls) -> bool:
        return cls.now().time() > cls.to_time(cls.END_TIME)

    @classmethod
    def is_morning(cls) -> bool:
        return cls.now().time() < cls.to_time(cls.START_TIME)

    @classmethod
    def is_working_hours(cls, dt: datetime | None = None) -> bool:
        if dt is None:
            dt = cls.now()
        return cls.to_time(cls.START_TIME) <= dt.time() <= cls.to_time(cls.END_TIME)

    @classmethod
    def is_working_day(cls, dt: datetime | str | None = None) -> bool:
        # todo #148 переделать если у нас остаются выходные, иначе грохнуть

        return True

        if dt is None:
            dt = cls.now()

        if isinstance(dt, str):
            dt = cls.to_datetime(dt)

        ex = DayExclusions()
        is_exclusion = ex.is_exclusion(dt)
        is_working_day = dt.weekday() < 5

        return is_working_day ^ is_exclusion  # xor

    @staticmethod
    def to_time(str_time) -> time:
        hours, minutes = map(int, str_time.split(':'))
        return time(hours, minutes)

    @classmethod
    def to_datetime(cls, str_date) -> datetime:
        return datetime.strptime(str_date, cls.DATE_FORMAT)

    @classmethod
    def get_current_date(cls) -> str:
        return cls.now().strftime(cls.DATE_FORMAT)

    @classmethod
    def get_previous_date(cls, dt: datetime | None = None) -> str:
        if dt is None:
            dt = cls.now()
        previous_datetime = dt - timedelta(days=1)
        return previous_datetime.strftime(cls.DATE_FORMAT)

    @classmethod
    def get_next_date(cls, dt: datetime | None = None) -> str:
        if dt is None:
            dt = cls.now()
        next_datetime = dt + timedelta(days=1)
        return next_datetime.strftime(cls.DATE_FORMAT)
