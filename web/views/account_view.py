from flask_admin.contrib.sqla import ModelView

from web.formater import view_format_datetime


class AccountView(ModelView):
    column_display_pk = True
    column_default_sort = [('id', False)]
    form_columns = [
        'id',
        'name',
        'status',
        'description',
        'updated_at',
    ]

    column_formatters = {
        'updated_at': view_format_datetime
    }

    column_editable_list = ['status']
    column_filters = ['status']
    form_choices = {
        'status': [
            (0, 'Off'),
            (1, 'Active')
        ]
    }
    column_choices = {
        'status': [
            (0, 'Off'),
            (1, 'Active')
        ]
    }
