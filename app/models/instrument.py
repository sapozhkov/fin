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

    def __repr__(self):
        return f"<Instrument {self.id} '{self.config}' [{self.account}] {'On' if self.status else 'Off'}>"

    @staticmethod
    def calculate_product(values):
        product = 1.0
        for value in values:
            if value and value > 0:
                product *= float(value)
        return (product - 1) * 100.0

    @property
    def profit_n_last_week(self):
        from app.models import Run
        one_week_ago = datetime.now(timezone.utc) - timedelta(weeks=1)
        profits = db.session.query(Run.profit_n).filter(
            Run.instrument == self.id,
            Run.date >= one_week_ago
        ).all()
        return self.calculate_product([profit[0] for profit in profits])

    @property
    def profit_n_last_month(self):
        from app.models import Run
        one_month_ago = datetime.now(timezone.utc) - timedelta(days=30)
        profits = db.session.query(Run.profit_n).filter(
            Run.instrument == self.id,
            Run.date >= one_month_ago
        ).all()
        return self.calculate_product([profit[0] for profit in profits])

    @property
    def profit_n_all_time(self):
        from app.models import Run
        profits = db.session.query(Run.profit_n).filter(
            Run.instrument == self.id
        ).all()
        return self.calculate_product([profit[0] for profit in profits])
