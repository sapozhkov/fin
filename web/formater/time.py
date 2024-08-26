from datetime import datetime, timedelta

from app import AppConfig


def format_time(value, _format='%H:%M'):
    """Форматирование даты и времени в указанный формат."""
    if isinstance(value, datetime):
        value += timedelta(hours=AppConfig.TIME_SHIFT_HOURS)  # Добавляем 3 часа
        return value.strftime(_format)
    return value  # Если значение не является datetime, возвращаем его без изменений
