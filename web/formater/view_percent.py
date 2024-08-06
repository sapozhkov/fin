from markupsafe import Markup


def view_format_percent(view, context, model, name):
    value = getattr(model, name)
    if not value:
        return "0"

    try:
        value = float(value)
    except ValueError:
        return value  # Если значение не может быть преобразовано в число, возвращаем его как есть

    color = "green" if value > 0 else "red"
    return Markup(f'<span style="color: {color};">{value:,.2f}%</span>')
