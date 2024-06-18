from flask_admin.contrib.sqla import ModelView

from app.command.constants import CommandStatus, CommandBotType, CommandType
from web import view_format_datetime


class CommandView(ModelView):
    column_display_pk = True
    column_default_sort = [('id', True)]
    form_columns = [
        'bot_type',
        'com_type',
        'run_id',
        'data',
        'status',
        'created_at',
        'expired_at',
        'executed_at'
    ]

    column_formatters = {
        'created_at': view_format_datetime,
        'expired_at': view_format_datetime,
        'executed_at': view_format_datetime
    }

    column_editable_list = ['status']
    column_filters = ['bot_type', 'run_id', 'status']
    form_choices = {
        'status': CommandStatus.get_list(),
        'bot_type': CommandBotType.get_list(),
        'com_type': CommandType.get_list(),
    }
    column_choices = {
        'status': CommandStatus.get_list(),
        'bot_type': CommandBotType.get_list(),
        'com_type': CommandType.get_list(),
    }
