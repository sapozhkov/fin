def view_format_class_name(view, context, model, name):
    value = str(getattr(model, name))
    if not value:
        return ""

    return value.split('.')[-1:][0]
