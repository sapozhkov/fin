from flask_admin.contrib.sqla import ModelView

from app.constants import RunStatus
from web import view_format_datetime
from web.formater import view_format_currency


class AccRunView(ModelView):
    column_display_pk = True
    column_default_sort = [('id', True)]
    form_columns = [
        'date',
        'status',
        'account_rel',
        'created_at',
        'updated_at',
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

    column_list = [
        'id',
        'date',
        'account_rel.name',
        'profit',
        'status',
        'open',
        'close',
        'high',
        'low',
        'created_at',
        'updated_at',
        'exit_code',
        'last_error',
        'profit_n',
        'data',
        'error_cnt'
    ]
    column_sortable_list = [
        'id',
        'date',
        'account_rel.name',
        'profit',
        'status',
        'open',
        'close',
        'high',
        'low',
        'created_at',
        'updated_at',
        'exit_code',
        'last_error',
        'profit_n',
        'data',
        'error_cnt'
    ]

    # form_columns = [
    #     'account',
    #     'date',
    #     'status',
    #     'account_rel',
    #     'created_at',
    #     'updated_at',
    #     'exit_code',
    #     'last_error',
    #     'open',
    #     'close',
    #     'high',
    #     'low',
    #     'profit',
    #     'profit_n',
    #     'data',
    #     'error_cnt'
    # ]
    column_labels = {
        'account_rel.name': 'Account',
    }

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
