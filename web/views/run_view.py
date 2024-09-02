from flask_admin.contrib.sqla import ModelView, filters
from flask_admin.contrib.sqla.filters import BaseSQLAFilter

from app.constants import RunStatus
from app.models import Instrument
from web.formater import view_format_datetime, view_format_currency


class Select2Filter(BaseSQLAFilter):
    def __init__(self, column, term, name=None):
        super().__init__(column, term)
        self.name = name or column
        self.term = term

    def apply(self, query, value, alias=None):
        return query.filter(Instrument.id == value)

    def operation(self):
        return 'equals'

    def __str__(self):
        return f'{self.name}: {self.term}'

    def get_options(self, view):
        return [(i.id, f"{i.name} ({i.account_rel.name})") for i in Instrument.get_for_filter()]


class RunView(ModelView):
    column_default_sort = [('date', True), ('id', False)]
    column_filters = (
        Select2Filter(column=Instrument.name, term='', name='Instrument'),
        'status',
        'date'
    )
    column_display_pk = True
    form_columns = (
        'instrument_rel', 'date', 'status', 'exit_code', 'last_error', 'total', 'depo',
        'profit', 'profit_n', 'expected_profit', 'data', 'config', 'start_cnt', 'end_cnt',
        'open', 'close', 'high', 'low',
        'created_at', 'updated_at',
        'error_cnt', 'operations_cnt'
    )
    form_choices = {'status': RunStatus.get_list()}
    column_choices = {'status': RunStatus.get_list()}
    column_formatters = {
        'created_at': view_format_datetime,
        'updated_at': view_format_datetime,
        'depo': view_format_currency,
        'open': view_format_currency,
        'close': view_format_currency,
        'high': view_format_currency,
        'low': view_format_currency,
    }

    def create_form(self, obj=None):
        form = super(RunView, self).create_form()
        form.instrument_rel.query_factory = lambda: Instrument.query.all()
        form.instrument_rel.label = lambda i: f"{i.name}"  # кастомное имя
        return form

    def edit_form(self, obj=None):
        form = super(RunView, self).edit_form(obj)
        form.instrument_rel.query_factory = lambda: Instrument.query.all()
        form.instrument_rel.label = lambda i: f"{i.name}"  # кастомное имя
        return form
