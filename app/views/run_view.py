from flask_admin.contrib.sqla import ModelView

from app import RunStatus
from app.models import Instrument


class RunView(ModelView):
    column_filters = ('instrument', 'instrument_rel', 'status', 'date')
    column_list = (
        'id', 'instrument_rel', 'date', 'status', 'exit_code', 'last_error', 'total', 'depo',
        'profit', 'data', 'config', 'start_cnt', 'end_cnt', 'candle', 'created_at', 'updated_at',
        'error_cnt', 'operations_cnt'
    )
    form_columns = (
        'instrument_rel', 'date', 'status', 'exit_code', 'last_error', 'total', 'depo',
        'profit', 'data', 'config', 'start_cnt', 'end_cnt', 'candle', 'created_at', 'updated_at',
        'error_cnt', 'operations_cnt'
    )
    form_choices = {'status': RunStatus.get_list()}
    column_choices = {'status': RunStatus.get_list()}

    def create_form(self, obj=None):
        form = super(RunView, self).create_form()
        form.instrument_rel.query_factory = lambda: Instrument.query.all()
        return form

    def edit_form(self, obj=None):
        form = super(RunView, self).edit_form(obj)
        form.instrument_rel.query_factory = lambda: Instrument.query.all()
        return form