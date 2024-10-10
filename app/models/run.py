from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import desc, not_
from sqlalchemy.orm import joinedload, aliased

from app import db
from app.config import AccConfig
from app.constants import RunStatus
from app.models import Instrument, Account, AccRun
from app.helper import TimeHelper


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
    expected_profit = db.Column(db.Float, default=0)
    profit = db.Column(db.Float, nullable=False)
    profit_n = db.Column(db.Float)
    data = db.Column(db.Text, nullable=True)
    instrument_data = db.Column(db.Text, nullable=True)
    config = db.Column(db.String, nullable=False)
    start_cnt = db.Column(db.Integer, nullable=False)
    end_cnt = db.Column(db.Integer, nullable=False)

    open = db.Column(db.Float)
    close = db.Column(db.Float)
    high = db.Column(db.Float)
    low = db.Column(db.Float)

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

    @staticmethod
    def get_current_runs_on_accounts():
        # Создаем алиас для модели Account
        account_alias = aliased(Account)

        # Запрос для получения всех текущих запусков с предзагрузкой связанных данных
        all_runs = Run.query \
            .join(Instrument) \
            .join(account_alias, Instrument.account_rel) \
            .filter(Run.date == TimeHelper.get_current_date()) \
            .options(joinedload(Run.instrument_rel).joinedload(Instrument.account_rel)) \
            .order_by(account_alias.name, Run.status, Run.config) \
            .all()

        # Группировка запусков по аккаунтам
        grouped_runs = defaultdict(list)
        for run in all_runs:
            grouped_runs[run.instrument_rel.account_rel.id].append(run)

        # выбираем AccRun текущего дня
        acc_runs = {acc_run.account: acc_run for acc_run in AccRun.get_today_runs()}

        # Формирование результирующего списка
        result = []
        for account_id, runs in grouped_runs.items():
            account = runs[0].instrument_rel.account_rel
            result.append({
                'account': account,
                'acc_run': acc_runs.get(account.id, None),
                'config': AccConfig.from_repr_string(account.config),
                'runs': runs
            })

        return result

    @staticmethod
    def get_active_runs_on_account(account_id: int) -> List['Run']:
        closed_statuses = RunStatus.closed_list()
        return Run.query\
            .join(Instrument)\
            .filter(
                Instrument.account == account_id,
                not_(Run.status.in_(closed_statuses))
            )\
            .all()

    @staticmethod
    def expire_unfinished():
        # Получаем список терминальных состояний
        closed_statuses = RunStatus.closed_list()

        # Находим все запуски, которые еще не находятся в терминальном состоянии
        non_terminal_runs = Run.query.filter(
            not_(Run.status.in_(closed_statuses))
        ).all()

        # Обновляем статус каждого запуска до терминального состояния
        for run in non_terminal_runs:
            run.status = RunStatus.FAILED
            run.updated_at = datetime.now(timezone.utc)

        # Сохраняем изменения
        db.session.commit()

        return len(non_terminal_runs)

    @staticmethod
    def get_by_date_and_ticker(date_str: str, ticker: str) -> List['Run']:
        """
        Получает все записи Run с указанной датой и содержащие подстроку в поле config.
        """
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError("Некорректный формат даты. Используйте формат 'YYYY-MM-DD'.")

        return Run.query.filter(
            Run.date == date,
            Run.config.ilike(f"%{ticker}%")
        ).all()

    @classmethod
    def get_by_id(cls, run_id) -> Optional['Run']:
        return cls.query.get(run_id)
