from datetime import datetime, timezone, time, timedelta


class TimeHelper:
    DATE_FORMAT = "%Y-%m-%d"

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
    def is_working_hours(cls, dt: datetime | None = None) -> bool:
        if dt is None:
            dt = cls.now()
        return cls.to_time(cls.START_TIME) <= dt.time() <= cls.to_time(cls.END_TIME)

    @staticmethod
    def to_time(str_time) -> time:
        hours, minutes = map(int, str_time.split(':'))
        return time(hours, minutes)

    @classmethod
    def get_current_date(cls) -> str:
        return cls.now().strftime(cls.DATE_FORMAT)

    @classmethod
    def get_previous_date(cls) -> str:
        previous_datetime = cls.now() - timedelta(days=1)
        return previous_datetime.strftime(cls.DATE_FORMAT)
