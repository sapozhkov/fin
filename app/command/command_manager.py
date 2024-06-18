from datetime import datetime, timezone
from typing import List

from sqlalchemy import or_

from app import db
from app.command.constants import CommandStatus, CommandBotType
from app.models import Command


class CommandManager:
    @staticmethod
    def create_command(
            com_type: int,
            run_id: int,
            data: str = '',
            bot_type: int = CommandBotType.TRADE_BOT,
            status: int = CommandStatus.NEW,
            expired_at=None
    ):
        command = Command(
            bot_type=bot_type,
            com_type=com_type,
            run_id=run_id,
            data=data,
            status=status,
            created_at=datetime.now(timezone.utc),
            expired_at=expired_at
        )
        db.session.add(command)
        db.session.commit()
        return command

    @staticmethod
    def update_command_status(command: Command, status):
        command.status = status
        command.executed_at = datetime.now(timezone.utc) if status in CommandStatus.closed_list() else None
        db.session.commit()
        return command

    @staticmethod
    def get_new_commands(run_id: int, bot_type: int = CommandBotType.TRADE_BOT) -> List[Command]:
        current_time = datetime.now(timezone.utc)
        return Command.query.filter(
            Command.bot_type == bot_type,
            Command.run_id == run_id,
            Command.status == CommandStatus.NEW,
            or_(Command.expired_at.is_(None), Command.expired_at <= current_time)
        ).all()
