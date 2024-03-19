import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

import pytz
from tinkoff.invest import OrderDirection


class AbstractAccountingHelper(ABC):
    def __init__(self):
        self.last_buy_price = 0.0
        self.last_sell_price = 0.0

    def add_deal_by_order(self, order):
        price = self.client.quotation_to_float(order.executed_order_price)
        if order.direction == OrderDirection.ORDER_DIRECTION_BUY:
            self.last_buy_price = price
        else:
            self.last_sell_price = price


class AccountingHelper(AbstractAccountingHelper):
    def __init__(self, file, client):
        super().__init__()
        file_path = Path(file)
        file_name = file_path.name.replace('.py', '')

        self.db_alg_name = f"{file_name}"
        self.db_file_name = 'db/trading_bot.db'

        self.client = client

    def add_deal_by_order(self, order):
        super().add_deal_by_order(order)
        price = self.client.quotation_to_float(order.executed_order_price)
        if order.direction == OrderDirection.ORDER_DIRECTION_BUY:
            price = -price
        commission = self.client.quotation_to_float(order.executed_commission, 2)
        # хак. иногда итоговая комиссия не проставляется в нужное поле
        if commission == 0:
            commission = self.client.quotation_to_float(order.initial_commission, 2)
        self.add_deal(
            order.direction,
            price,
            commission,
            round(price - commission, 2)
        )

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
