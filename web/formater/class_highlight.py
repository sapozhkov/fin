from app.constants import RunStatus


def format_currency_class(value):
    if not value:
        return ''
    if value < 0:
        return 'text-danger'
    elif value > 0:
        return 'text-success'
    else:
        return ''


def format_status_class(status):
    if status == RunStatus.WORKING:
        return 'text-primary'
    elif status == RunStatus.FINISHED:
        return 'text-success'
    elif status == RunStatus.SLEEPING:
        return 'text-warning'
    elif status == RunStatus.FAILED:
        return 'text-danger'
    else:
        return ''
