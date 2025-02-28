from app import db
from app.models import Instrument


class InstrumentLog(db.Model):
    __tablename__ = 'instruments_log'

    id = db.Column(db.Integer, primary_key=True)
    instrument_id = db.Column(db.Integer, nullable=False)
    updated_at = db.Column(db.DateTime)
    config = db.Column(db.String(256), nullable=False)
    data = db.Column(db.Text, nullable=True)
    expected_profit = db.Column(db.Float, default=0)

    instrument_rel = db.relationship(
        'Instrument', primaryjoin='foreign(InstrumentLog.instrument_id) == Instrument.id', backref='logs'
    )

    @classmethod
    def add_by_instrument(cls, instrument: Instrument, data=''):
        log = cls(
            instrument_id=instrument.id,
            updated_at=instrument.updated_at,
            config=instrument.config,
            data=data,
            expected_profit=instrument.expected_profit,
        )

        db.session.add(log)
        db.session.commit()

    def __repr__(self):
        return f"<InstrumentLog {self.id} i{self.ins} '{self.config}' exp_profit {self.expected_profit}>"
