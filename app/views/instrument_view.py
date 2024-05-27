from flask_admin.contrib.sqla import ModelView


class InstrumentView(ModelView):
    column_list = ('id', 'name', 'account', 'config', 'status')
    form_columns = ('name', 'account', 'config', 'status')
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
