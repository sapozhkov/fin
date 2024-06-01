from datetime import datetime
from pathlib import Path

import pytz

from bot.db import HistoricalTrade
from bot.env import AbstractAccountingHelper


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
