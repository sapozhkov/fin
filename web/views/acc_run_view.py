from flask import url_for
from flask_admin.contrib.sqla import ModelView
from markupsafe import Markup

from app.constants import RunStatus
from app.models import AccRun
from web import view_format_datetime
from web.filter.account_filter import AccountFilter
from web.formater import view_format_currency, view_format_percent


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
        'account_rel.name',
        'date',
        'profit',
        'status',
        'open',
        'close',
        'high',
        'low',
        'created_at',
        'updated_at',
        'exit_code',
        'error_cnt'
    ]
    column_sortable_list = [
        'id',
        'account_rel.name',
        'date',
        'profit',
        'status',
        'open',
        'close',
        'high',
        'low',
        'created_at',
        'updated_at',
        'exit_code',
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
        'profit': view_format_percent,
        'date': lambda view, context, model, name: Markup(
            f'<a style="white-space: pre;" href="{url_for("chartsview.balance", acc_run_id=model.id)}" >{getattr(model, name)}</a>'
        )
    }

    column_filters = [
        AccountFilter(column=AccRun.account, term='', name='Account'),
        'status',
        'date'
    ]
    form_choices = {'status': RunStatus.get_list()}
    column_choices = {'status': RunStatus.get_list()}
