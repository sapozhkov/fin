from flask_login import UserMixin
from app import login, db


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
    ticker = db.Column(db.String(10), nullable=False)
    server = db.Column(db.Integer, nullable=False)
    config = db.Column(db.String(256), nullable=False)
    status = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"<Instrument {self.id} '{self.config}' {self.config}>"


class Run(db.Model):
    __tablename__ = 'runs'

    id = db.Column(db.Integer, primary_key=True)
    instrument = db.Column(db.Integer, db.ForeignKey('instruments.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
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

    # Связь с моделью Instruments
    instrument_rel = db.relationship('Instruments', backref=db.backref('runs', lazy=True))

    # Индексы
    __table_args__ = (
        db.Index('idx_date', 'instrument', 'date'),
    )

    def __repr__(self):
        return f'<Run {self.instrument} ({self.config}) on {self.date}>'

    # Метод для получения связанного инструмента
    def get_instrument(self):
        return Instrument.query.get(self.instrument)


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
