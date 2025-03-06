from datetime import datetime, timezone, timedelta
from typing import Optional, List

from app import db


class Instrument(db.Model):
    __tablename__ = 'instruments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    account = db.Column(db.BigInteger, db.ForeignKey('accounts.id', name='fk_instruments_account'), nullable=False)
    config = db.Column(db.String(256), nullable=False)
    base_config = db.Column(db.String(256), nullable=False)
    status = db.Column(db.Integer, nullable=False)
    data = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float)
    expected_profit = db.Column(db.Float, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    account_rel = db.relationship('Account', back_populates='instruments')

    _profit_n_last_day = None
    _profit_n_last_week = None
    _profit_n_last_month = None
    _profit_n_all_time = None

    def save(self):
        self.updated_at = datetime.now(timezone.utc)
        db.session.add(self)
        db.session.commit()

    @classmethod
    def get_by_id(cls, instrument_id) -> Optional['Instrument']:
        return cls.query.get(instrument_id)

    @classmethod
    def get_all_active(cls) -> List['Instrument']:
        return cls.query.filter_by(status=1).order_by(cls.updated_at).all()

    @classmethod
    def get_all_with_active_acc(cls) -> List['Instrument']:
        """
        Возвращает все инструменты, у которых аккаунт активен (status=1).
        """
        from app.models import Account  # Импорт модели Account

        return cls.query.join(Account).filter(
            Account.status == 1  # Аккаунт активен
        ).order_by(cls.updated_at).all()

    @classmethod
    def get_instruments_cnt_by_acc_id(cls, account_id, only_active=False) -> int:
        return cls.query.filter(
            Instrument.account == account_id,
            Instrument.status == 1
        ).count() if only_active else cls.query.filter(Instrument.account == account_id).count()

    @classmethod
    def get_for_filter(cls) -> List['Instrument']:
        return cls.query.order_by(cls.name).all()

    def __repr__(self):
        return f"<Instrument {self.id} '{self.config}' [{self.account}] {'On' if self.status else 'Off'}>"

    @staticmethod
    def calculate_product(values):
        product = 1.0
        for value in values:
            if value and value > 0:
                product *= float(value)
        return round((product - 1) * 100.0, 2)

    def _calculate_profit_n(self, time_frame):
        from app.models import Run
        profits = db.session.query(Run.profit_n).filter(
            Run.instrument == self.id,
            Run.date >= time_frame
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
