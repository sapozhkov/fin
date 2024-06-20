from flask_admin.contrib.sqla import ModelView

from web.formater import view_format_datetime


class InstrumentLogView(ModelView):
    column_display_pk = True
    column_default_sort = ('id', True)
    column_filters = ['instrument_id']
    column_formatters = {
        'updated_at': view_format_datetime
    }
