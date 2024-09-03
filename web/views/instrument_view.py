from flask import url_for
from flask_admin.contrib.sqla import ModelView
from markupsafe import Markup
from wtforms import ValidationError

from app.config import RunConfig
from web.formater import view_format_datetime, view_format_currency, view_format_percent


class InstrumentView(ModelView):
    column_display_pk = True
    column_default_sort = [('account', False), ('id', False)]
    column_list = (
        'id',
        'profit_n_last_day',
        'profit_n_last_week',
        'profit_n_last_month',
        'profit_n_all_time',
        'name',
        'account_rel.name',
        'config',
        'expected_profit',
        'price',
        'data',
        'updated_at',
        'status',

    )
    column_sortable_list = (
        'id', 'name', 'account_rel.name', 'config', 'status',
        'expected_profit', 'price', 'data', 'updated_at',
    )
    column_formatters = {
        'updated_at': view_format_datetime,
        'price': view_format_currency,
        'profit_n_last_day': view_format_percent,
        'profit_n_last_week': view_format_percent,
        'profit_n_last_month': view_format_percent,
        'profit_n_all_time': lambda view, context, model, name: Markup(
            f'<a href="{InstrumentView.make_runs_rel(model.id)}" >'
            f'{view_format_percent(view, context, model, name)}</a>'
        ),
    }
    column_editable_list = ['status']
    column_filters = [
        'status',
        'account_rel.name'
    ]
    column_choices = {
        'status': [
            (0, 'Off'),
            (1, 'Active')
        ]
    }
    column_labels = {
        'account_rel.name': 'Account',
    }

    form_columns = ('name', 'account_rel', 'config', 'status', 'data', 'expected_profit', 'price')
    form_choices = {
        'status': [
            (0, 'Off'),
            (1, 'Active')
        ]
    }

    # это для перехвата ошибки при некорректном формате ввода конфига
    def on_model_change(self, form, model, is_created):
        try:
            RunConfig.from_repr_string(model.config)
        except ValueError as e:
            raise ValidationError(str(e))

        # Вызываем родительский метод для продолжения стандартной обработки
        super(InstrumentView, self).on_model_change(form, model, is_created)

    @staticmethod
    def make_runs_rel(instrument_id):
        return url_for("run.index_view", flt1_0=instrument_id)
