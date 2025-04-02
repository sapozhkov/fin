from datetime import datetime, timezone, timedelta
from typing import List

import pytz
from tinkoff.invest import Client, InvestError, InstrumentIdType, OrderType, OrderDirection, CandleInterval

from app.dto import BoughtInstrumentDto
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
    def get_current_price_from_last_candle(figi: str) -> float | None:
        """
        Получает текущую цену для заданного FIGI, используя данные последней свечи с интервалом 1 минута.

        :param figi: Идентификатор инструмента (FIGI).
        :return: Текущая цена (float) на основе цены закрытия последней свечи.
        """
        # Используем pytz для работы с часовыми поясами, например UTC
        now = datetime.now(pytz.UTC)
        # Запрашиваем свечи за последние 5 минут, чтобы гарантировать наличие свежих данных
        start_time = now - timedelta(minutes=5)

        with Client(AppConfig.TOKEN) as client:
            try:
                candles_response = client.market_data.get_candles(
                    figi=figi,
                    from_=start_time,
                    to=now,
                    interval=CandleInterval.CANDLE_INTERVAL_1_MIN
                )
            except InvestError as e:
                print(f"Ошибка при получении последних свечей: {e}")
                return None

            # Проверяем, что свечи получены
            if candles_response.candles:
                last_candle = candles_response.candles[-1]
                return q2f(last_candle.close)
            else:
                return None

    @staticmethod
    def get_last_price(figi: str) -> float | None:
        """
        Отдает последнюю цену для указанного инструмента (по figi)
        :param figi: str
        :return: float
        """
        prices = TinkoffApi.get_last_prices([figi])
        return prices.get(figi, None)

    # @staticmethod
    # def get_first_account_id() -> str:
    #     """
    #     Получает идентификатор первого аккаунта пользователя
    #     :return: идентификатор первого аккаунта
    #     """
    #     with Client(AppConfig.TOKEN) as client:
    #         accounts = client.users.get_accounts().accounts
    #         if accounts:
    #             first_account_id = accounts[0].id
    #             return first_account_id
    #         else:
    #             raise Exception("No accounts found")
    #
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
    def get_account_balance_rub(account_id) -> float:
        """
        Получает баланс аккаунта пользователя в рублях
        :return: Баланс счета в рублях
        """
        with Client(AppConfig.TOKEN) as client:
            try:
                response = client.operations.get_portfolio(account_id=str(account_id))
                return q2f(response.total_amount_portfolio)
            except InvestError as e:
                print(f"Ошибка при получении баланса: {e}")
                return 0

    @staticmethod
    def get_ticker_by_figi(figi):
        with Client(AppConfig.TOKEN) as client:
            try:
                response = client.instruments.get_instrument_by(
                    id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI, id=figi)
                return response.instrument.ticker
            except InvestError as e:
                print(f"An error occurred for FIGI {figi}: {e}")
        return None

    @staticmethod
    def get_shares_on_account(account_id) -> List[BoughtInstrumentDto]:
        instruments = []
        with Client(AppConfig.TOKEN) as client:
            try:
                response = client.operations.get_portfolio(account_id=str(account_id))
                for position in response.positions:
                    if position.instrument_type != 'share':
                        continue
                    instruments.append(BoughtInstrumentDto(
                        figi=position.figi,
                        ticker=TinkoffApi.get_ticker_by_figi(position.figi),
                        quantity=position.quantity.units,
                    ))
            except InvestError as e:
                print(f"Ошибка при получении инструментов на аккаунте: {e}")
        return instruments

    @staticmethod
    def sell(account_id, figi, quantity):
        with Client(AppConfig.TOKEN) as client:
            try:
                # Создаем ордер на продажу по лучшей цене, так как это работает почти всегда в отличие от рыночного
                client.orders.post_order(
                    figi=figi,
                    quantity=quantity,
                    account_id=str(account_id),
                    order_type=OrderType.ORDER_TYPE_BESTPRICE,
                    direction=OrderDirection.ORDER_DIRECTION_SELL,
                    order_id=str(datetime.now(timezone.utc)),
                )
                print(f"Sold {quantity} of {figi}")
            except InvestError as e:
                print(f"An error occurred: {e}")
