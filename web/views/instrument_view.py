from flask_admin.contrib.sqla import ModelView
from wtforms import ValidationError

from app.config import RunConfig


class InstrumentView(ModelView):
    def scaffold_list_columns(self):
        # Получаем все колонки модели
        columns = super(InstrumentView, self).scaffold_list_columns()
        # Убедитесь, что 'id' включен в список колонок
        if 'id' not in columns:
            columns.insert(0, 'id')
        return columns

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
            RunConfig.from_repr_string(model.config)
        except ValueError as e:
            raise ValidationError(e)

        # Вызываем родительский метод для продолжения стандартной обработки
        super(InstrumentView, self).on_model_change(form, model, is_created)

