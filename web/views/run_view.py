from flask import url_for
from flask_admin.contrib.sqla import ModelView
from markupsafe import Markup

from app.constants import RunStatus
from app.models import Instrument, Run
from web.filter import InstrumentFilter
from web.formater import view_format_datetime, view_format_currency


class RunView(ModelView):
    column_default_sort = [('date', True), ('id', False)]
    column_filters = (
        InstrumentFilter(column=Run.instrument, term='', name='Instrument'),
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
        'date': lambda view, context, model, name: Markup(
            f'<a href="{url_for("chartsview.run", run_id=model.id)}" >{getattr(model, name)}</a>'
        )
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
