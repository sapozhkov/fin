from datetime import datetime, timedelta

import pytz


def view_format_datetime(view, context, model, name):
    value = getattr(model, name)
    if not value:
        return ""

    # Применение сдвига +3 часа
    value = value.replace(tzinfo=pytz.utc).astimezone(pytz.timezone('Europe/Moscow'))

    now = datetime.now(pytz.timezone('Europe/Moscow'))
    diff = now - value

    if diff < timedelta(days=1):
        return value.strftime('%H:%M')
    elif diff < timedelta(days=7):
        return value.strftime('%d %H:%M')
    else:
        return value.strftime('%Y-%m-%d %H:%M')
