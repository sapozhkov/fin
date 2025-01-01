from datetime import datetime
from typing import List

from app.command.constants import CommandType
from app.config import AccConfig
from app.models import Run, Instrument, Account
from bot import TestAlgorithm
from bot.env import AbstractAccDbHelper


class AccDbTestEnvHelper(AbstractAccDbHelper):
    def __init__(self, bot_alg_list: List[TestAlgorithm], config: AccConfig):
        self.bot_alg_list = bot_alg_list
        self.config = config

    def get_instruments_by_acc_id(self, account_id: str | int) -> List[Instrument]:
        # return Instrument.query.filter_by(account=int(account_id)).all()
        # todo проверить в боевом тесте
        out = []
        for bot_id, bot_alg in enumerate(self.bot_alg_list):
            instrument = Instrument(
                id=bot_id + 1,
                config=str(bot_alg.config),
                name=bot_alg.config.name,
            )
            out.append(instrument)
        return out

    def get_today_runs_by_instrument_list(self, instruments: List[Instrument], today: datetime.date) \
            -> list[tuple[int]]:
        # return Run.query.filter(
        #     Run.date == today,
        #     Run.instrument.in_([instrument.id for instrument in instruments])
        # ).with_entities(Run.instrument).distinct().all()
        # -> [(3,), (4,)]
        # todo проверить в боевом тесте
        out = []
        for bot_id, bot_alg in enumerate(self.bot_alg_list):
            # todo проверить, что тут есть запуски и есть отказы
            if not bot_alg.process_this_day:
                continue

            out.append((bot_id + 1, ))

        return out

    def get_active_runs_on_account(self, account_id) -> List[Run]:
        # closed_statuses = RunStatus.closed_list()
        # return Run.query\
        #     .join(Instrument)\
        #     .filter(
        #         Instrument.account == int(account_id),
        #         not_(Run.status.in_(closed_statuses))
        #     )\
        #     .all()

        # todo проверить в боевом тесте
        out = []
        for bot_id, bot_alg in enumerate(self.bot_alg_list):
            if not bot_alg.bot.continue_trading():
                continue

            run = Run(
                id=bot_id + 1,
                config=str(bot_alg.config),
            )
            out.append(run)
        return out

    def create_command(self, command_type: int, run_id: int):
        """
        Пока реализовано прямыми вызовами команд
        Чуть отличается от прод логики, но этим можно пренебречь
        Как доберемся до более сложных механик команд можно будет реализовать проброс
        :param command_type:
        :param run_id:
        :return:
        """
        for bot_id, bot_alg in enumerate(self.bot_alg_list):
            if run_id == bot_id + 1:
                if command_type == CommandType.STOP:
                    bot_alg.bot.stop()
                elif command_type == CommandType.STOP_ON_ZERO:
                    bot_alg.bot.stop(True)

        # тут нужен объект для хранения команд. он же будет в запусках использоваться
        # CommandManager.create_command(command_type, run_id)

    def get_acc_by_id(self, account_id: str) -> Account:
        return Account(
            id=account_id,
            name=account_id,
            config=str(self.config),
            balance=0,
        )

    def commit_changes(self, state):
        pass

    def add_balance_row(self, run_state, cur_balance, param):
        pass
