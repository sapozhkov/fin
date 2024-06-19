from flask_admin.contrib.sqla import ModelView
from wtforms import ValidationError

from app.config import RunConfig
from web.formater import view_format_datetime


class InstrumentView(ModelView):
    column_display_pk = True
    column_default_sort = [('account', False), ('id', False)]
    column_list = ('id', 'name', 'account_rel.name', 'config',
                   'expected_profit', 'price', 'data', 'updated_at', 'status')
    column_sortable_list = ('id', 'name', 'account_rel.name', 'config', 'status',
                            'expected_profit', 'price', 'data', 'updated_at')
    column_formatters = {
        'updated_at': view_format_datetime,
    }
    column_editable_list = ['status']
    column_filters = [
        'status',
        'account_rel.name'
    ]
    column_choices = {
        'status': [
            (0, 'Off'),
            (1, 'Active')
        ]
    }
    column_labels = {
        'account_rel.name': 'Account',
    }

    form_columns = ('name', 'account_rel', 'config', 'status', 'data', 'expected_profit', 'price')
    form_choices = {
        'status': [
            (0, 'Off'),
            (1, 'Active')
        ]
    }

    def on_model_change(self, form, model, is_created):
        try:
            RunConfig.from_repr_string(model.config)
        except ValueError as e:
            raise ValidationError(e)

        # Вызываем родительский метод для продолжения стандартной обработки
        super(InstrumentView, self).on_model_change(form, model, is_created)
