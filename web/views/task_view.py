from flask_admin.contrib.sqla import ModelView

from app.constants import TaskStatus
from web.formater import view_format_datetime, view_format_class_name


class TaskView(ModelView):
    column_default_sort = [('id', True), ('id', False)]
    column_display_pk = True
    column_formatters = {
        'class_name': view_format_class_name,
        'created_at': view_format_datetime,
        'updated_at': view_format_datetime,
    }
    form_choices = {'status': TaskStatus.get_list()}
    column_choices = {'status': TaskStatus.get_list()}
