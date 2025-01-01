from datetime import datetime
from typing import List, Optional

from app import db
from app.command import CommandManager
from app.models import Instrument, Run, Account, AccRun, AccRunBalance
from bot.env import AbstractAccDbHelper


class AccDbHelper(AbstractAccDbHelper):
    def get_instruments_by_acc_id(self, account_id: str | int) -> List[Instrument]:
        return Instrument.query.filter_by(account=int(account_id)).all()

    def get_today_runs_by_instrument_list(self, instruments: List[Instrument], today: datetime.date)\
            -> list[tuple[int]]:
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
        #278 можно объединить с предыдущим методом, так как ночью закрываются все незакрытые с ошибкой
            и останется только отфильтровать по статусу
        :param account_id:
        :return:
        """
        return Run.get_active_runs_on_account(account_id)

    def create_command(self, command_type: int, run_id: int):
        CommandManager.create_command(command_type, run_id)

    def get_acc_by_id(self, account_id: str) -> Account:
        account = Account.get_by_id(account_id)
        if account is None:
            raise ValueError(f"Не найден account c account_id='{account_id}'")
        return account

    def commit_changes(self, state: AccRun):
        """
        Сохранение в базу изменений. Также в этом методе происходит сохранение измененной записи Account,
        помимо указанной напрямую state
        :param state:
        :return:
        """
        if not state.id:
            db.session.add(state)

        db.session.commit()

    def add_balance_row(self, acc_run: AccRun | None, cur_balance: float, timestamp: datetime):
        if acc_run is None:
            return

        row = AccRunBalance(
            acc_run=acc_run.id,
            balance=cur_balance,
            datetime=timestamp
        )
        db.session.add(row)
        db.session.commit()

