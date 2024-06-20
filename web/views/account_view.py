from flask_admin.contrib.sqla import ModelView
from wtforms import ValidationError

from app.config import AccConfig
from web.formater import view_format_datetime, view_format_currency


class AccountView(ModelView):
    column_display_pk = True
    column_default_sort = [('id', False)]
    form_columns = [
        'id',
        'name',
        'status',
        'config',
        'balance',
        'description',
        'updated_at',
    ]

    column_formatters = {
        'updated_at': view_format_datetime,
        'balance': view_format_currency,
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

    def on_model_change(self, form, model, is_created):
        try:
            AccConfig.from_repr_string(model.config)
        except ValueError as e:
            raise ValidationError(e)

        # Вызываем родительский метод для продолжения стандартной обработки
        super(AccountView, self).on_model_change(form, model, is_created)
