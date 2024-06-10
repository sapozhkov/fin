from flask_admin.contrib.sqla import ModelView

from web.formater import view_format_datetime


class TaskView(ModelView):
    column_default_sort = [('id', True), ('id', False)]
    column_display_pk = True
    column_formatters = {
        'created_at': view_format_datetime,
        'updated_at': view_format_datetime
    }
