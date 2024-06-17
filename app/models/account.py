from datetime import datetime, timezone
from typing import Optional

from app import db


class Account(db.Model):
    __tablename__ = 'accounts'

    id = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    instruments = db.relationship('Instrument', back_populates='account_rel')

    def __repr__(self):
        return f"<Account {self.name} ({self.id}) {'On' if self.status else 'Off'}>"

    @classmethod
    def get_by_id(cls, acc_id) -> Optional['Account']:
        return cls.query.get(acc_id)

