from .currency import format_currency


def view_format_currency(view, context, model, name):
    value = getattr(model, name)
    if not value:
        return ""

    try:
        value = float(value)
    except ValueError:
        return value  # Если значение не может быть преобразовано в число, возвращаем его как есть

    return format_currency(value)
