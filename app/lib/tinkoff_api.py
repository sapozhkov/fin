from tinkoff.invest import Client, InvestError

from app.helper import q2f
from app.config import AppConfig


class TinkoffApi:
    @staticmethod
    def get_last_prices(figi_list: list) -> dict:
        """
        Отдает последние цены для перечисленных инструментов (по figi)
        :param figi_list:
        :return: {figi: float, ...}
        """
        out = {}
        with Client(AppConfig.TOKEN) as client:
            try:
                # Получаем последние цены для каждого инструмента в списке FIGI
                response = client.market_data.get_last_prices(figi=figi_list)

                for last_price in response.last_prices:
                    figi = last_price.figi
                    price = q2f(last_price.price)
                    out[figi] = price
            finally:
                return out

    @staticmethod
    def get_last_price(figi: str) -> float:
        """
        Отдает последнюю цену для указанного инструмента (по figi)
        :param figi: str
        :return: float
        """
        prices = TinkoffApi.get_last_prices([figi])
        return prices.get(figi, None)

    @staticmethod
    def get_first_account_id() -> str:
        """
        Получает идентификатор первого аккаунта пользователя
        :return: идентификатор первого аккаунта
        """
        with Client(AppConfig.TOKEN) as client:
            accounts = client.users.get_accounts().accounts
            if accounts:
                first_account_id = accounts[0].id
                return first_account_id
            else:
                raise Exception("No accounts found")

    # @staticmethod
    # def get_account_balance() -> dict[dict] | None:
    #     """
    #     Получает баланс первого аккаунта пользователя
    #     :return: Словарь с балансом счета
    #     """
    #     account_id = TinkoffApi.get_first_account_id()
    #     with Client(AppConfig.TOKEN) as client:
    #         try:
    #             response = client.operations.get_portfolio(account_id=account_id)
    #             balance = {}
    #             for position in response.positions:
    #                 balance[position.figi] = {
    #                     "figi": position.figi,
    #                     "quantity": q2f(position.quantity),
    #                     "current_price": q2f(position.current_price),
    #                     "average_position_price": q2f(position.average_position_price)
    #                 }
    #             return balance
    #         except InvestError as e:
    #             print(f"Ошибка при получении баланса: {e}")
    #             return None

    @staticmethod
    def get_account_balance_rub() -> float:
        """
        Получает баланс первого аккаунта пользователя в рублях
        :return: Баланс счета в рублях
        """
        account_id = TinkoffApi.get_first_account_id()
        with Client(AppConfig.TOKEN) as client:
            try:
                response = client.operations.get_portfolio(account_id=account_id)
                return q2f(response.total_amount_portfolio)
            except InvestError as e:
                print(f"Ошибка при получении баланса: {e}")
                return 0
