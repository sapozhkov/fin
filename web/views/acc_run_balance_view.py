from flask_admin.contrib.sqla import ModelView

from web import view_format_datetime
from web.formater import view_format_currency


class AccRunBalanceView(ModelView):
    column_display_pk = True
    column_default_sort = [('id', False)]
    form_columns = [
        'acc_run',
        'balance',
        'datetime'
    ]

    column_formatters = {
        'datetime': view_format_datetime,
        'balance': view_format_currency,
    }

    column_filters = ['acc_run', 'datetime']
