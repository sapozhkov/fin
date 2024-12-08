from markupsafe import Markup


def view_format_preserve_newlines(view, context, model, name):
    """
    Форматирование текста для сохранения переводов строк и предотвращения автоматических переносов.

    :param view: Объект представления (не используется).
    :param context: Контекст (не используется).
    :param model: Модель, содержащая данные.
    :param name: Имя поля в модели.
    :return: Отформатированный текст.
    """
    value = getattr(model, name, "")
    if not value:
        return ""

    # Удаляем лишние пробелы
    formatted_value = value.replace(" ", "&nbsp;")  # Заменяем пробелы на неразрывные
    return Markup(f'<span style="white-space: pre;">{formatted_value}</span>')
