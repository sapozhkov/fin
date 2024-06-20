from flask_admin.contrib.sqla import ModelView

from app.constants import RunStatus
from web import view_format_datetime
from web.formater import view_format_currency


class AccRunView(ModelView):
    column_display_pk = True
    column_default_sort = [('id', True)]
    form_columns = [
        'account',
        'date',
        'created_at',
        'updated_at',
        'status',
        'exit_code',
        'last_error',
        'open',
        'close',
        'high',
        'low',
        'profit',
        'profit_n',
        'data',
        'error_cnt'
    ]

    column_formatters = {
        'created_at': view_format_datetime,
        'updated_at': view_format_datetime,
        'open': view_format_currency,
        'close': view_format_currency,
        'high': view_format_currency,
        'low': view_format_currency,
    }

    column_filters = ['account', 'status', 'date']
    form_choices = {'status': RunStatus.get_list()}
    column_choices = {'status': RunStatus.get_list()}
