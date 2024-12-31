from abc import ABC, abstractmethod
from typing import List

from app.dto import BoughtInstrumentDto


class AbstractAccClient(ABC):
    @abstractmethod
    def get_account_balance_rub(self, account_id: str) -> float:
        pass

    @abstractmethod
    def get_shares_on_account(self, account_id) -> List[BoughtInstrumentDto]:
        pass

    @abstractmethod
    def sell(self, account_id: str, figi: str, quantity: int):
        pass
