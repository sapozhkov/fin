from datetime import datetime
from typing import List

from app.command import CommandManager
from app.models import Instrument, Run
from bot.env import AbstractDbProxy


class DbProxy(AbstractDbProxy):
    def get_instruments_by_acc_id(self, account_id: str | int) -> List[Instrument]:
        return Instrument.query.filter_by(account=int(account_id)).all()

    def get_today_runs_by_instrument_list(self, instruments: List[Instrument], today: datetime.date) -> List[Run]:
        """
        Выдает все запуски, что запущены за сегодня
        :param instruments:
        :param today:
        :return:
        """
        return Run.query.filter(
            Run.date == today,
            Run.instrument.in_([instrument.id for instrument in instruments])
        ).with_entities(Run.instrument).distinct().all()

    def get_active_runs_on_account(self, account_id) -> List[Run]:
        """
        Отдает все запущенные в текущий момент Run записи (исключает закрытые статусы)
        todo можно объеденить с предыдущим методом, так как ночью закрываются все незакрытые с ошибкой
            и останется только отфильтровать по статусу
        :param account_id:
        :return:
        """
        return Run.get_active_runs_on_account(account_id)

    def create_command(self, command_type: int, run_id: int):
        CommandManager.create_command(command_type, run_id)
