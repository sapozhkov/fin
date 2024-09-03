from flask_admin.contrib.sqla import ModelView

from app.models import InstrumentLog
from web.filter import InstrumentFilter
from web.formater import view_format_datetime


class InstrumentLogView(ModelView):
    column_display_pk = True
    column_default_sort = ('id', True)
    column_filters = [InstrumentFilter(column=InstrumentLog.instrument_id, term='', name='Instrument'),]
    column_formatters = {
        'updated_at': view_format_datetime
    }
