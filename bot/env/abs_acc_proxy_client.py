from abc import ABC, abstractmethod


class AbstractAccProxyClient(ABC):
    @staticmethod
    @abstractmethod
    def get_account_balance_rub(account_id: str) -> float:
        pass

    @staticmethod
    @abstractmethod
    def get_shares_on_account(account_id):
        pass

    @staticmethod
    @abstractmethod
    def sell(account_id: str, figi: str, quantity: int):
        pass
