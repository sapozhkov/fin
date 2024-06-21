from typing import List

from app import db
from app.constants import RunStatus
from app.helper import TimeHelper


class AccRun(db.Model):
    __tablename__ = 'acc_runs'

    id = db.Column(db.Integer, primary_key=True)
    account = db.Column(db.BigInteger, db.ForeignKey('accounts.id', name='fk_acc_run_account'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)
    status = db.Column(db.Integer, nullable=False)
    exit_code = db.Column(db.Integer, nullable=False)
    last_error = db.Column(db.String, nullable=True)

    open = db.Column(db.Float)
    close = db.Column(db.Float)
    high = db.Column(db.Float)
    low = db.Column(db.Float)

    profit = db.Column(db.Float)
    profit_n = db.Column(db.Float)
    data = db.Column(db.Text, nullable=True)
    error_cnt = db.Column(db.Integer, nullable=False, server_default='0')

    account_rel = db.relationship('Account')

    # Индексы
    __table_args__ = (
        db.Index('idx_acc_date', 'account', 'date'),
    )

    def get_status_title(self):
        return RunStatus.get_title(self.status)

    @staticmethod
    def get_today_runs() -> List['AccRun']:
        today = TimeHelper.get_current_date()
        return AccRun.query.filter(AccRun.date == today).all()

    def __repr__(self):
        return f'<AccRun {self.id} a{self.account} at {self.date}>'
