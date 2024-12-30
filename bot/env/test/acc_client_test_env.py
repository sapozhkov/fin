from bot.env import AbstractAccClient


class TestAccClientEnvHelper(AbstractAccClient):
    @staticmethod
    def get_account_balance_rub(account_id: str) -> float:
        # todo implement
        pass

    @staticmethod
    def get_shares_on_account(account_id):
        # todo implement
        pass

    @staticmethod
    def sell(account_id: str, figi: str, quantity: int):
        # todo implement
        pass
