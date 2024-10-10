from datetime import datetime
from pathlib import Path

import pytz
from tinkoff.invest import OrderType, OrderDirection, PostOrderResponse

from app.constants import HistoryOrderType
from bot.db import HistoricalTrade
from bot.env import AbstractAccountingHelper
from bot.helper import OrderHelper


class AccountingHelper(AbstractAccountingHelper):
    def __init__(self, file, client, time):
        super().__init__(client, time)
        file_path = Path(file)
        file_name = file_path.name.replace('.py', '')

        self.db_alg_name = f"{file_name}"
        self.historical_trade = HistoricalTrade()

    def add_executed_order(self, order_type, order_direction, price, count, commission, total):
        if order_type == OrderType.ORDER_TYPE_MARKET:
            type_ = HistoryOrderType.BUY_MARKET if order_direction == OrderDirection.ORDER_DIRECTION_BUY \
                else HistoryOrderType.SELL_MARKET
        else:
            type_ = HistoryOrderType.EXECUTED_BUY_LIMIT if order_direction == OrderDirection.ORDER_DIRECTION_BUY \
                else HistoryOrderType.EXECUTED_SELL_LIMIT

        self.historical_trade.add_deal(
            self.run_id,
            order_type,
            self.time.now(),
            price,
            count,
            commission,
            total
        )

    def add_order(self, order: PostOrderResponse):
        lots = OrderHelper.get_lots(order)
        avg_price = self.client.round(OrderHelper.get_avg_price(order))
        if order.order_type == OrderType.ORDER_TYPE_MARKET:
            type_ = HistoryOrderType.BUY_MARKET if order.direction == OrderDirection.ORDER_DIRECTION_BUY \
                else HistoryOrderType.SELL_MARKET
        else:
            type_ = HistoryOrderType.OPEN_BUY_LIMIT if order.direction == OrderDirection.ORDER_DIRECTION_BUY \
                else HistoryOrderType.OPEN_SELL_LIMIT

        self.historical_trade.add_deal(
            self.run_id,
            type_,
            self.time.now(),
            avg_price,
            lots,
            OrderHelper.get_commission(order),
            self.client.round(lots * avg_price)
        )

    def get_instrument_count(self):
        return self.client.get_instruments_count()
