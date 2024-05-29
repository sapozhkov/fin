from flask_admin.contrib.sqla import ModelView
from wtforms import ValidationError

from dto.config_dto import ConfigDTO


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

    def on_model_change(self, form, model, is_created):
        try:
            ConfigDTO.from_repr_string(model.config)
        except ValueError as e:
            raise ValidationError(e)

        # Вызываем родительский метод для продолжения стандартной обработки
        super(InstrumentView, self).on_model_change(form, model, is_created)

