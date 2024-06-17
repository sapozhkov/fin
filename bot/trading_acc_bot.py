import random
from datetime import time as datetime_time
from typing import Tuple

from app import db
from app.config import AccConfig
from app.lib import TinkoffApi
from bot import AbstractBot
from app.constants import RunStatus
from app.helper import TimeHelper
from app.models import AccRun, Account
from bot.env.prod import LoggerHelper, TimeProdEnvHelper
from bot.env import AbstractLoggerHelper, AbstractTimeHelper


class TradingAccountBot(AbstractBot):
    # todo abs?
    STATE_NEW = 1
    STATE_WORKING = 2
    STATE_FINISHED = 3

    # количество секунд задержки старта работы в начале торгового дня. хак, чтобы не влететь в отсечку утром
    START_SEC_SHIFT = 1

    def __init__(
            self,
            config: AccConfig,
            time_helper: AbstractTimeHelper | None = None,
            logger_helper: AbstractLoggerHelper | None = None,
    ):
        # хелперы и DTO
        self.config = config
        self.time = time_helper or TimeProdEnvHelper()

        account_id = self.config.account_id
        self.account = Account.get_by_id(account_id)
        if not self.account:
            raise ValueError(f"Не найден account c account_id='{account_id}'")

        self.logger = logger_helper or LoggerHelper(__name__, self.account.name)

        if not self.is_trading_day():
            self.log("Не торговый день. Завершаем работу.")
            self.state = self.STATE_FINISHED
            return

        # внутренние переменные
        self.state = self.STATE_NEW

        self.open_balance = self.get_current_balance()
        self.cur_balance = self.open_balance
        
        self.run_state: AccRun | None = None
        if self.account:
            self.run_state = AccRun(
                account=self.account.id,
                date=self.time.now().date(),
                created_at=self.time.now(),
                updated_at=self.time.now(),
                status=RunStatus.NEW,
                exit_code=0,
                last_error='',
                open=self.open_balance,
                close=self.open_balance,
                high=self.open_balance,
                low=self.open_balance,
                profit=0,
                profit_n=1,
                data='',
                error_cnt=0,
            )
            self.save_run_state()

        self.log(f"INIT \n"
                 f"     config - {self.config}\n"
                 f"     account - {self.account}\n"
                 f"     run_instance - {self.run_state}"
                 )

    # todo abs? вместе с time 
    def is_trading_day(self):
        return TimeHelper.is_working_day(self.time.now())

    # todo -//-
    def log(self, message, repeat=False):
        self.logger.log(message, repeat)

    # todo -//-
    def can_trade(self) -> Tuple[bool, int]:
        """
        Проверяет доступна ли торговля.
        Отдает статус "можно торговать" и количество секунд для задержки, если нет
        :return: (bool, int)
        """
        now = self.time.now()
        now_time = now.time()

        start_hour_str, start_min_str = self.config.start_time.split(':')
        end_hour_str, end_min_str = self.config.end_time.split(':')

        start_time = datetime_time(int(start_hour_str), int(start_min_str), self.START_SEC_SHIFT)
        end_time = datetime_time(int(end_hour_str), int(end_min_str))

        # ко времени запуска приближаемся шагами в половину оставшегося времени
        if now_time < start_time:
            now_sec = now_time.hour * 3600 + now_time.minute * 60 + now_time.second
            start_sec = start_time.hour * 3600 + start_time.minute * 60 + start_time.second
            delta_seconds = start_sec - now_sec
            return False, max(2, round(delta_seconds / 2))

        if now_time >= end_time:
            self.stop()
            return False, 0

        return True, 0

    def get_status_str(self) -> str:
        out = f"balance {self.cur_balance} "

        if self.run_state:
            out += f"[o{self.run_state.open} " \
                   f"l{self.run_state.low} " \
                   f"h{self.run_state.high} " \
                   f"c{self.run_state.close}]"

        return out

    def get_current_balance(self) -> float | None:
        return TinkoffApi.get_account_balance_rub(self.account.id)

    # todo ->
    def continue_trading(self):
        return self.state != self.STATE_FINISHED

    # todo ->
    def run(self):
        while self.continue_trading():
            self.run_iteration()
        self.log('END')

    def start(self):
        """Начало работы скрипта. первый старт"""

        if self.state != self.STATE_NEW:
            return

        self.state = self.STATE_WORKING
        
        self.log(f"START")

        if self.run_state:
            self.run_state.status = RunStatus.WORKING
            self.save_run_state()

    def run_iteration(self):
        can_trade, sleep_sec = self.can_trade()
        if not can_trade:
            if sleep_sec:
                self.log(f"can not trade, sleep {TimeProdEnvHelper.get_remaining_time_text(sleep_sec)}")
                if self.run_state:
                    self.run_state.status = RunStatus.SLEEPING
                    self.save_run_state()
                self.time.sleep(sleep_sec)
            return

        self.cur_balance = self.get_current_balance()

        self.start()

        if self.check_need_stop():
            self.stop(to_zero=True)
            return

        self.time.sleep(self.config.sleep_trading)

    def check_need_stop(self):
        if not (self.config.stop_up_p or self.config.stop_down_p):
            return False

        need_up_t = self.round(self.open_balance * (1 + self.config.stop_up_p))
        if self.config.stop_up_p and self.cur_balance > need_up_t:
            self.log(f"Останавливаем по получению нужного уровня прибыли. "
                     f"cur_balance={self.cur_balance}, stop_up_p={self.config.stop_up_p}, need_up_t={need_up_t}")
            return True

        need_down_t = self.round(self.open_balance * (1 - self.config.stop_down_p))
        if self.config.stop_down_p and self.cur_balance < need_down_t:
            self.log(f"Останавливаем по достижению критического уровня потерь. "
                     f"cur_balance={self.cur_balance}, stop_up_p={self.config.stop_down_p}, need_down_t={need_down_t}")
            return True

        return False

    def stop(self, to_zero=False, exit_code=0):
        if self.state == self.STATE_FINISHED:
            return

        self.state = self.STATE_FINISHED

        self.log("Остановка бота...")

        # todo #186 to_zero - надо "занулиться" при выходе

        if self.run_state:
            self.run_state.exit_code = exit_code
            self.run_state.status = RunStatus.FINISHED if not exit_code else RunStatus.FAILED

            self.save_run_state()

    def save_run_state(self):
        state = self.run_state

        if state is None:
            return

        if not state.id:
            db.session.add(state)

        state.updated_at = self.time.now()
        state.close = self.cur_balance
        if self.cur_balance > state.high:
            state.high = self.cur_balance
        if self.cur_balance < state.low:
            state.low = self.cur_balance

        if state.open:
            state.profit = self.round(100 * (state.close - state.open) / state.open)
        state.profit_n = self.round(1 + state.profit / 100)

        state.data = self.get_status_str()

        state.last_error = f"{self.time.now()} - {self.logger.last_error}" \
            if self.logger.last_error else ''
        state.error_cnt = self.logger.error_cnt

        db.session.commit()

    @staticmethod
    def round(val):
        return round(val, 2)
