from datetime import datetime, timezone, timedelta
from typing import Optional, List

from app import db


class Instrument(db.Model):
    __tablename__ = 'instruments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    account = db.Column(db.BigInteger, db.ForeignKey('accounts.id', name='fk_instruments_account'), nullable=False)
    config = db.Column(db.String(256), nullable=False)
    status = db.Column(db.Integer, nullable=False)
    data = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float)
    expected_profit = db.Column(db.Float, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    account_rel = db.relationship('Account', back_populates='instruments')

    profit_n_last_day_cache = None
    profit_n_last_week_cache = None
    profit_n_last_month_cache = None
    profit_n_all_time_cache = None

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
    def get_all(cls) -> List['Instrument']:
        return cls.query.order_by(cls.status.desc()).all()

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
