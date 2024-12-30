from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from app.models import Instrument, Run, Account


class AbstractAccDbHelper(ABC):
    @abstractmethod
    def get_instruments_by_acc_id(self, account_id: str | int) -> List[Instrument]:
        pass

    @abstractmethod
    def get_today_runs_by_instrument_list(self, instruments: List[Instrument], today: datetime.date) -> List[Run]:
        pass

    @abstractmethod
    def get_active_runs_on_account(self, account_id) -> List[Run]:
        pass

    @abstractmethod
    def create_command(self, command_type: int, run_id: int):
        pass

    @abstractmethod
    def get_acc_by_id(self, account_id: str) -> Optional[Account]:
        pass
