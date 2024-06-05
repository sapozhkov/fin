from typing import Optional

from app import db


class Instrument(db.Model):
    __tablename__ = 'instruments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    account = db.Column(db.Integer, nullable=False)
    config = db.Column(db.String(256), nullable=False)
    status = db.Column(db.Integer, nullable=False)

    @classmethod
    def get_by_id(cls, instrument_id) -> Optional['Instrument']:
        return cls.query.get(instrument_id)

    def __repr__(self):
        return f"<Instrument {self.id} '{self.config}' [{self.account}] {'On' if self.status else 'Off'}>"
