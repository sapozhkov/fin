from datetime import datetime, timezone, timedelta
from typing import Optional, List

from app import db


class Account(db.Model):
    __tablename__ = 'accounts'

    id = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    balance = db.Column(db.Float)
    balance_correction = db.Column(db.Float, nullable=True)
    status = db.Column(db.Integer, nullable=False)
    config = db.Column(db.String)
    description = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    instruments = db.relationship('Instrument', back_populates='account_rel')

    _profit_n_last_day = None
    _profit_n_last_week = None
    _profit_n_last_month = None
    _profit_n_all_time = None
    _total_instruments_cnt = None
    _active_instruments_cnt = None

    def __repr__(self):
        return f"<Account {self.name} ({self.id}) /{self.config}/ {'On' if self.status else 'Off'}>"

    @classmethod
    def get_by_id(cls, acc_id: int | str) -> Optional['Account']:
        return cls.query.get(int(acc_id))

    @classmethod
    def get_for_filter(cls) -> List['Account']:
        return cls.query.order_by(cls.name).all()

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
        if self._profit_n_last_day is not None:
            return self._profit_n_last_day

        one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
        self._profit_n_last_day = self._calculate_profit_n(one_day_ago)

        return self._profit_n_last_day

    @property
    def profit_n_last_week(self):
        if self._profit_n_last_week is not None:
            return self._profit_n_last_week

        one_week_ago = datetime.now(timezone.utc) - timedelta(weeks=1)
        self._profit_n_last_week = self._calculate_profit_n(one_week_ago)

        return self._profit_n_last_week

    @property
    def profit_n_last_month(self):
        if self._profit_n_last_month is not None:
            return self._profit_n_last_month

        one_month_ago = datetime.now(timezone.utc) - timedelta(days=30)
        self._profit_n_last_month = self._calculate_profit_n(one_month_ago)

        return self._profit_n_last_month

    @property
    def profit_n_all_time(self):
        if self._profit_n_all_time is not None:
            return self._profit_n_all_time

        self._profit_n_all_time = self._calculate_profit_n(datetime.min)

        return self._profit_n_all_time

    @property
    def total_instruments_cnt(self):
        if self._total_instruments_cnt is not None:
            return self._total_instruments_cnt

        self._total_instruments_cnt = self.get_instruments_cnt_by_acc_id()

        return self._total_instruments_cnt

    @property
    def active_instruments_cnt(self):
        if self._active_instruments_cnt is not None:
            return self._active_instruments_cnt

        self._active_instruments_cnt = self.get_instruments_cnt_by_acc_id(True)

        return self._active_instruments_cnt

    def get_instruments_cnt_by_acc_id(self, only_active=False) -> int:
        """
        Возвращает все инструменты, у которых аккаунт активен (status=1).
        """
        from app.models import Instrument  # Импорт модели Account
        return Instrument.get_instruments_cnt_by_acc_id(self.id, only_active)
