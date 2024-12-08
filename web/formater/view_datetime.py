from datetime import datetime, timedelta

import pytz
import locale

from markupsafe import Markup

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
        formatted_value = value.strftime('%H:%M')
    elif diff < timedelta(days=7):
        formatted_value = value.strftime('%a, %H:%M')
    else:
        formatted_value = value.strftime('%Y-%m-%d %H:%M')

    return Markup(f'<span style="white-space: pre;">{formatted_value}</span>')
