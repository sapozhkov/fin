from flask_admin.contrib.sqla import ModelView

from web import view_format_datetime


class AccRunBalanceView(ModelView):
    column_display_pk = True
    column_default_sort = [('id', False)]
    form_columns = [
        'acc_run',
        'balance',
        'datetime'
    ]

    column_formatters = {
        'datetime': view_format_datetime
    }

    column_filters = ['acc_run', 'datetime']
