from flask_admin.contrib.sqla import ModelView

from app.constants import RunStatus
from app.models import Instrument


class RunView(ModelView):
    column_default_sort = [('date', True), ('id', False)]
    column_filters = ('instrument', 'instrument_rel', 'status', 'date')
    column_display_pk = True
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
