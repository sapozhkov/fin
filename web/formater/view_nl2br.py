from .nl2br import nl2br


def view_nl2br(view, context, model, name):
    value = getattr(model, name)

    if not value:
        return ""

    return nl2br(value)
