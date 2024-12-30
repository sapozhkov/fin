from datetime import datetime
from typing import List, Optional

from app.models import Run, Instrument, Account
from bot.env import AbstractAccDbHelper


class AccDbTestEnvHelper(AbstractAccDbHelper):
    def get_instruments_by_acc_id(self, account_id: str | int) -> List[Instrument]:
        # должен быть доступ к списку инструментов

        # todo implement
        # надо отдать список инструментов
        # берем список инструментов их загруженных
        # собираем их и отдаем
        pass

    def get_today_runs_by_instrument_list(self, instruments: List[Instrument], today: datetime.date) -> List[Run]:
        # todo implement
        pass

    def get_active_runs_on_account(self, account_id) -> List[Run]:
        # todo implement
        pass

    def create_command(self, command_type: int, run_id: int):
        # todo implement
        pass

    def get_acc_by_id(self, account_id: str) -> Optional[Account]:
        return None
