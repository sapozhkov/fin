from datetime import datetime, timezone, timedelta
from typing import Optional

from app import db


class Account(db.Model):
    __tablename__ = 'accounts'

    id = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    balance = db.Column(db.Float)
    status = db.Column(db.Integer, nullable=False)
    config = db.Column(db.String)
    description = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    instruments = db.relationship('Instrument', back_populates='account_rel')

    profit_n_last_day_cache = None
    profit_n_last_week_cache = None
    profit_n_last_month_cache = None
    profit_n_all_time_cache = None

    def __repr__(self):
        return f"<Account {self.name} ({self.id}) /{self.config}/ {'On' if self.status else 'Off'}>"

    @classmethod
    def get_by_id(cls, acc_id) -> Optional['Account']:
        return cls.query.get(acc_id)

    @staticmethod
    def calculate_product(values):
        product = 1.0
        for value in values:
            if value and value > 0:
                product *= float(value)
        return round((product - 1) * 100.0, 2)

    def _calculate_profit_n(self, time_frame):
        from app.models import AccRun
        profits = db.session.query(AccRun.profit_n).filter(
            AccRun.account == self.id,
            AccRun.date >= time_frame
        ).all()

        return self.calculate_product([profit[0] for profit in profits])

    @property
    def profit_n_last_day(self):
        if self.profit_n_last_day_cache is not None:
            return self.profit_n_last_day_cache

        one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
        self.profit_n_last_day_cache = self._calculate_profit_n(one_day_ago)

        return self.profit_n_last_day_cache

    @property
    def profit_n_last_week(self):
        if self.profit_n_last_week_cache is not None:
            return self.profit_n_last_week_cache

        one_week_ago = datetime.now(timezone.utc) - timedelta(weeks=1)
        self.profit_n_last_week_cache = self._calculate_profit_n(one_week_ago)

        return self.profit_n_last_week_cache

    @property
    def profit_n_last_month(self):
        if self.profit_n_last_month_cache is not None:
            return self.profit_n_last_month_cache

        one_month_ago = datetime.now(timezone.utc) - timedelta(days=30)
        self.profit_n_last_month_cache = self._calculate_profit_n(one_month_ago)

        return self.profit_n_last_month_cache

    @property
    def profit_n_all_time(self):
        if self.profit_n_all_time_cache is not None:
            return self.profit_n_all_time_cache

        self.profit_n_all_time_cache = self._calculate_profit_n(datetime.min)

        return self.profit_n_all_time_cache