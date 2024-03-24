import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

import pytz
from tinkoff.invest import OrderDirection

from helper.tinkoff_client import AbstractProxyClient


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
            self.num += 1
        else:
            self.last_sell_price = price
            self.num -= 1

        commission = self.client.quotation_to_float(order.executed_commission, 2)
        # хак. иногда итоговая комиссия не проставляется в нужное поле
        if commission == 0:
            commission = self.client.quotation_to_float(order.initial_commission, 2)

        total = round(price - commission, 2)

        self.sum += total

        self.add_deal(
            order.direction,
            price,
            commission,
            total
        )

    @abstractmethod
    def add_deal(self, deal_type, price, commission, total):
        pass

    def reset(self):
        self.sum = 0


class AccountingHelper(AbstractAccountingHelper):
    def __init__(self, file, client):
        super().__init__(client)
        file_path = Path(file)
        file_name = file_path.name.replace('.py', '')

        self.db_alg_name = f"{file_name}"
        self.db_file_name = 'db/trading_bot.db'

    def add_deal(self, deal_type, price, commission, total):
        my_timezone = pytz.timezone('Europe/Moscow')
        datetime_with_tz = datetime.now(my_timezone).strftime('%Y-%m-%d %H:%M:%S %z')

        conn = sqlite3.connect(self.db_file_name)
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO deals (algorithm_name, type, instrument, datetime, price, commission, total)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (self.db_alg_name, deal_type, self.client.ticker, datetime_with_tz, price, commission, total))
        conn.commit()
        conn.close()
