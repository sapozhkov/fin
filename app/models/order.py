from typing import List

from app import db
from app.models import Instrument


class Order(db.Model):
    __tablename__: str = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    run = db.Column(db.Integer, db.ForeignKey('runs.id'), nullable=False)
    type = db.Column(db.Integer, nullable=False)
    datetime = db.Column(db.DateTime, nullable=True)
    price = db.Column(db.Float, nullable=False)
    commission = db.Column(db.Float, nullable=False, default=0)
    total = db.Column(db.Float, nullable=False)
    count = db.Column(db.Integer, nullable=False, server_default='1')

    # Связь с моделью Instruments
    run_rel = db.relationship('Run', backref=db.backref('run', lazy=True))

    def __repr__(self):
        return f'<Order {self.id} - {self.datetime} - {self.type} - ' \
               f'{self.price} x {self.count} + {self.commission} = {self.total}>'

    # Метод для получения связанного инструмента
    def get_instrument(self):
        return Instrument.query.get(self.instrument)

    @staticmethod
    def get_by_run_id(run_id: int) -> List['Order']:
        return Order.query.filter_by(run=run_id).order_by(Order.datetime).all()
