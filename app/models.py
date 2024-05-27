from typing import Optional

from flask_login import UserMixin
from sqlalchemy import desc

from app import login, db, RunStatus
from lib.time_helper import TimeHelper


class User(UserMixin):
    id = 1  # Уникальный идентификатор для пользователя


@login.user_loader
def load_user(user_id):
    if user_id == "1":
        return User()
    return None


class Instrument(db.Model):
    __tablename__ = 'instruments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    account = db.Column(db.Integer, nullable=False)
    config = db.Column(db.String(256), nullable=False)
    status = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"<Instrument {self.id} '{self.config}' [{self.account}] {'On' if self.status else 'Off'}>"


class Run(db.Model):
    __tablename__ = 'runs'

    id = db.Column(db.Integer, primary_key=True)
    instrument = db.Column(db.Integer, db.ForeignKey('instruments.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)
    status = db.Column(db.Integer, nullable=False)
    exit_code = db.Column(db.Integer, nullable=False)
    last_error = db.Column(db.String, nullable=True)
    total = db.Column(db.Float, nullable=False)
    depo = db.Column(db.Float, nullable=False)
    profit = db.Column(db.Float, nullable=False)
    data = db.Column(db.Text, nullable=True)
    config = db.Column(db.String, nullable=False)
    start_cnt = db.Column(db.Integer, nullable=False)
    end_cnt = db.Column(db.Integer, nullable=False)
    candle = db.Column(db.String, nullable=False)
    error_cnt = db.Column(db.Integer, nullable=False, server_default='0')
    operations_cnt = db.Column(db.Integer, nullable=False, server_default='0')

    # Связь с моделью Instrument
    instrument_rel = db.relationship('Instrument', backref=db.backref('runs', lazy=True))

    # Индексы
    __table_args__ = (
        db.Index('idx_date', 'instrument', 'date'),
    )

    def __repr__(self):
        return f'<Run {self.id} i{self.instrument} ({self.config}) at {self.date}>'

    # Метод для получения связанного инструмента
    def get_instrument(self):
        return Instrument.query.get(self.instrument)

    @staticmethod
    def get_prev_run(instrument_id: int) -> Optional['Run']:
        return Run.query\
            .filter(Run.date < TimeHelper.get_current_date(), Run.instrument == instrument_id)\
            .order_by(desc(Run.id)).first()

    def get_status_title(self):
        return RunStatus.get_title(self.status)


class Deal(db.Model):
    __tablename__ = 'deals'

    id = db.Column(db.Integer, primary_key=True)
    run = db.Column(db.Integer, db.ForeignKey('runs.id'), nullable=False)
    type = db.Column(db.Integer, nullable=False)
    datetime = db.Column(db.DateTime, nullable=True)
    price = db.Column(db.Float, nullable=False)
    commission = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)
    count = db.Column(db.Integer, nullable=False, server_default='1')

    # Связь с моделью Instruments
    run_rel = db.relationship('Run', backref=db.backref('run', lazy=True))

    def __repr__(self):
        return f'<Deal {self.id} - {self.datetime} - {self.type} - ' \
               f'{self.price} x {self.count} + {self.commission} = {self.total}>'

    # Метод для получения связанного инструмента
    def get_instrument(self):
        return Instrument.query.get(self.instrument)


# Функция для получения Instrument по id
def get_instrument_by_id(instrument_id) -> Instrument | None:
    instrument = Instrument.query.get(instrument_id)
    if instrument is None:
        return None  # Объект не найден
    return instrument  # Объект найден
