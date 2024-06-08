from flask_admin.contrib.sqla import ModelView


class TaskView(ModelView):
    column_default_sort = [('id', True), ('id', False)]
    column_display_pk = True
