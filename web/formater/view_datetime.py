from datetime import datetime, timedelta

import pytz
import locale

# Устанавливаем русскую локаль
locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')


def view_format_datetime(view, context, model, name):
    value = getattr(model, name)
    if not value:
        return ""

    # Применение сдвига +3 часа
    value = value.replace(tzinfo=pytz.utc).astimezone(pytz.timezone('Europe/Moscow'))

    now = datetime.now(pytz.timezone('Europe/Moscow'))
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    diff = now - value

    if value >= today:
        return value.strftime('%H:%M')
    elif diff < timedelta(days=7):
        return value.strftime('%a %H:%M')
    else:
        return value.strftime('%Y-%m-%d %H:%M')
