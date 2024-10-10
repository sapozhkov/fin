from pathlib import Path

from app import db
from app.models import Order
from bot.env import AbstractAccountingHelper


class AccountingHelper(AbstractAccountingHelper):
    def __init__(self, file, client, time):
        super().__init__(client, time)
        file_path = Path(file)
        file_name = file_path.name.replace('.py', '')

        self.db_alg_name = f"{file_name}"

    def register_order(self, order: Order):
        db.session.add(order)
        db.session.commit()

    def get_instrument_count(self):
        return self.client.get_instruments_count()
