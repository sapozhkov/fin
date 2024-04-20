import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

import pytz
from tinkoff.invest import OrderDirection, PostOrderResponse

from lib.historical_trade import HistoricalTrade
from prod_env.tinkoff_client import AbstractProxyClient


class AbstractAccountingHelper(ABC):
    def __init__(self, client):
        self.last_buy_price = 0.0
        self.last_sell_price = 0.0
        self.sum = 0
        self.num = 0
        self.client: AbstractProxyClient = client

    def add_deal_by_order(self, order):
        price = self.client.quotation_to_float(order.executed_order_price)

        if order.direction == OrderDirection.ORDER_DIRECTION_BUY:
            self.last_buy_price = price
            price = -price
            self.num += order.lots_executed
        else:
            self.last_sell_price = price
            self.num -= order.lots_executed

        commission = self.client.quotation_to_float(order.executed_commission)
        # хак. иногда итоговая комиссия не проставляется в нужное поле
        if commission == 0:
            commission = self.client.quotation_to_float(order.initial_commission)

        total = round(price - commission, 2)

        self.sum += total

        self.add_deal(
            order.direction,
            self.client.round(price / order.lots_executed),
            order.lots_executed,
            self.client.round(commission / order.lots_executed),
            total
        )

    def add_order(self, order: PostOrderResponse):
        pass

    def del_order(self, order: PostOrderResponse):
        pass

    @abstractmethod
    def add_deal(self, deal_type, price, count, commission, total):
        pass

    @abstractmethod
    def get_instrument_count(self):
        pass

    def reset(self):
        self.sum = 0

    def get_num(self):
        return self.num

    def set_num(self, num):
        self.num = num

    def get_sum(self):
        return self.sum


class AccountingHelper(AbstractAccountingHelper):
    def __init__(self, file, client):
        super().__init__(client)
        file_path = Path(file)
        file_name = file_path.name.replace('.py', '')

        self.db_alg_name = f"{file_name}"
        self.historical_trade = HistoricalTrade()

    def add_deal(self, deal_type, price, count, commission, total):
        my_timezone = pytz.timezone('Europe/Moscow')
        datetime_with_tz = datetime.now(my_timezone).strftime('%Y-%m-%d %H:%M:%S %z')

        self.historical_trade.add_deal(
            self.db_alg_name,
            deal_type,
            self.client.ticker,
            datetime_with_tz,
            price,
            count,
            commission,
            total
        )

    def get_instrument_count(self):
        return self.client.get_instruments_count()
