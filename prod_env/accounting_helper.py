from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

import pytz
from tinkoff.invest import OrderDirection, PostOrderResponse

from bot.db import HistoricalTrade
from bot.helper import OrderHelper
from prod_env.tinkoff_client import AbstractProxyClient


class AbstractAccountingHelper(ABC):
    def __init__(self, client):
        self.sum = 0
        self.num = 0
        self.operations_cnt = 0
        self.client: AbstractProxyClient = client
        self.order_helper = OrderHelper(self.client)

    def add_deal_by_order(self, order):
        lots = self.order_helper.get_lots(order)
        avg_price = self.order_helper.get_avg_price(order)
        commission = self.order_helper.get_commission(order)

        if order.direction == OrderDirection.ORDER_DIRECTION_BUY:
            avg_price = -avg_price
            self.num += lots
        else:
            self.num -= lots

        total = round(avg_price * lots - commission, 2)

        self.sum += total

        self.operations_cnt += 1

        self.add_deal(
            order.direction,
            avg_price,
            lots,
            self.client.round(commission / lots),
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
            self.client.instrument.ticker,
            datetime_with_tz,
            price,
            count,
            commission,
            total
        )

    def get_instrument_count(self):
        return self.client.get_instruments_count()
