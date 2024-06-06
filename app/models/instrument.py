from datetime import datetime, UTC
from typing import Optional, List

from app import db


class Instrument(db.Model):
    __tablename__ = 'instruments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    account = db.Column(db.Integer, nullable=False)
    config = db.Column(db.String(256), nullable=False)
    status = db.Column(db.Integer, nullable=False)
    expected_profit = db.Column(db.Float, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))

    def save(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def get_by_id(cls, instrument_id) -> Optional['Instrument']:
        return cls.query.get(instrument_id)

    @classmethod
    def get_all_active(cls) -> List['Instrument']:
        return cls.query.filter_by(status=1).order_by(cls.updated_at).all()

    def __repr__(self):
        return f"<Instrument {self.id} '{self.config}' [{self.account}] {'On' if self.status else 'Off'}>"
