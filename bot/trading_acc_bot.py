from datetime import timedelta
from typing import Optional

from app import db
from app.command.constants import CommandType
from app.config import AccConfig, RunConfig
from bot import AbstractBot
from app.constants import RunStatus
from app.models import AccRun, Account, AccRunBalance
from bot.env.abs_acc_db_helper import AbstractAccDbHelper
from bot.env.prod import LoggerHelper, TimeProdEnvHelper, TinkoffAccClient, AccDbHelper
from bot.env import AbstractLoggerHelper, AbstractTimeHelper, AbstractAccClient


class TradingAccountBot(AbstractBot):

    TICKS_TO_STOP = 5

    def __init__(
            self,
            config: AccConfig,
            time_helper: Optional[AbstractTimeHelper] = None,
            logger_helper: Optional[AbstractLoggerHelper] = None,
            acc_client: Optional[AbstractAccClient] = None,
            db_: Optional[AbstractAccDbHelper] = None,
    ):
        # todo расхождение типов. config.account_id - str,  self.account_id и Account.id - int (#181)
        self.account_id: str = config.account_id if config.account_id != '0' else ''

        self.acc_client: AbstractAccClient = acc_client or TinkoffAccClient()
        self.db: AbstractAccDbHelper = db_ or AccDbHelper()

        account: Optional[Account] = self.db.get_acc_by_id(self.account_id)
        if not account and self.account_id:
            raise ValueError(f"Не найден account c account_id='{self.account_id}'")

        super().__init__(
            config,
            time_helper or TimeProdEnvHelper(),
            logger_helper or LoggerHelper(__name__, account.name if account else self.account_id)
        )

        if not self.is_trading_day():
            self.log("Не торговый день. Завершаем работу.")
            self.state = self.STATE_FINISHED
            return

        self.open_balance = self.get_current_balance() or 0
        self.cur_balance = self.open_balance

        self.exiting = False
        '''Флаг: инициирован процесс выхода'''

        self.sell_all_on_exit = False
        '''Флаг: Распродать все при выходе'''

        self.need_stop_up_cnt = 0
        '''Счетчик срабатываний для выхода по верхней планке'''

        self.need_stop_down_cnt = 0
        '''Счетчик срабатываний для выхода по нижней планке'''

        self.run_state: AccRun | None = None
        if account:
            account.balance = self.open_balance

            self.run_state = AccRun(
                account=int(self.account_id),
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
            self.update_run_state()

            # self.save_balance_to_log()

        self.log(f"INIT \n"
                 f"     config - {self.config}\n"
                 f"     account - {account}\n"
                 f"     run_instance - {self.run_state}"
                 )

    def get_status_str(self) -> str:
        out = f"balance {self.cur_balance} "

        if self.run_state:
            out += f"[o{self.run_state.open} " \
                   f"l{self.run_state.low} " \
                   f"h{self.run_state.high} " \
                   f"c{self.run_state.close}]"

        return out

    def get_current_balance(self) -> float | None:
        return self.acc_client.get_account_balance_rub(self.account_id)

    def sell_unused_instruments(self):
        # Запросить все инструменты на аккаунте
        instruments = self.db.get_instruments_by_acc_id(self.account_id)

        # Выбрать сегодняшние запуски
        today = self.time.now().date()
        active_instruments = self.db.get_today_runs_by_instrument_list(instruments, today)

        active_instrument_ids = {ai[0] for ai in active_instruments}

        used_tickers = [RunConfig.from_repr_string(instrument.config).ticker
                        for instrument in instruments if instrument.id in active_instrument_ids]

        self.log(f"Используемые инструменты {used_tickers}")

        bought_instruments = self.acc_client.get_shares_on_account(self.account_id)

        self.log(f"Купленные инструменты {bought_instruments}")

        for instrument in bought_instruments:
            if instrument.ticker not in used_tickers:
                self.log(f"Продажа инструмента: {instrument.ticker}, {instrument.quantity} шт")
                self.acc_client.sell(self.account_id, instrument.figi, instrument.quantity)

    def sell_all_instruments(self):
        bought_instruments = self.acc_client.get_shares_on_account(self.account_id)

        for instrument in bought_instruments:
            self.log(f"Продажа инструмента: {instrument.ticker}, {instrument.quantity} шт")
            self.acc_client.sell(self.account_id, instrument.figi, instrument.quantity)

    def start(self):
        """Начало работы скрипта. первый старт"""

        if self.state != self.STATE_NEW:
            return

        self.state = self.STATE_WORKING
        
        self.log(f"START")

        self.sell_unused_instruments()

        if self.run_state:
            self.run_state.status = RunStatus.WORKING
            self.update_run_state()

    def run_iteration(self):
        can_trade, sleep_sec = self.can_trade()
        if not can_trade:
            if sleep_sec:
                self.log(f"can not trade, sleep {TimeProdEnvHelper.get_remaining_time_text(sleep_sec)}")
                if self.run_state:
                    self.run_state.status = RunStatus.SLEEPING
                    self.update_run_state()
                self.time.sleep(sleep_sec)
            return

        self.cur_balance = self.get_current_balance()

        self.save_balance_to_log()

        self.start()

        if not self.exiting and self.check_need_stop():
            # выбираем все не завершенные
            runs = self.db.get_active_runs_on_account(self.account_id)

            # добавляем каждому команду выхода
            for run in runs:
                self.db.create_command(CommandType.STOP_ON_ZERO, run.id)
                self.log(f"Команда на остановку для запуска {run}")

            # в конфиге делаем сдвиг на 5 мин от текущего времени и выходим
            new_stop_time = self.time.now() + timedelta(minutes=5)
            self.config.end_time = new_stop_time.strftime('%H:%M')
            self.log(f"Планируем остановку бота в  {self.config.end_time}")

            # взводим флаг полной распродажи
            self.sell_all_on_exit = True

            # взводим флаг выхода
            self.exiting = True

        # обновление состояния в базе
        self.update_run_state()

        self.time.sleep(self.config.sleep_trading)

    def check_need_stop(self):
        if not (self.config.stop_up_p or self.config.stop_down_p):
            return False

        need_up_t = self.round(self.open_balance * (1 + self.config.stop_up_p / 100))
        if self.config.stop_up_p and self.cur_balance > need_up_t:
            self.need_stop_up_cnt += 1
            if self.need_stop_up_cnt >= self.TICKS_TO_STOP:
                self.log(f"Останавливаем по получению нужного уровня прибыли. "
                         f"cur_balance={self.cur_balance}, stop_up_p={self.config.stop_up_p}, need_up_t={need_up_t}")
                return True
            else:
                self.log(f"Останавливаем по получению нужного уровня прибыли. Шаг {self.need_stop_up_cnt}")
                return False

        need_down_t = self.round(self.open_balance * (1 - self.config.stop_down_p / 100))
        if self.config.stop_down_p and self.cur_balance < need_down_t:
            self.need_stop_down_cnt += 1
            if self.need_stop_down_cnt >= self.TICKS_TO_STOP:
                self.log(f"Останавливаем по достижению критического уровня потерь. "
                         f"cur_balance={self.cur_balance}, stop_down_p={self.config.stop_down_p}, need={need_down_t}")
                return True
            else:
                self.log(f"Останавливаем по получению нужного уровня потерь. Шаг {self.need_stop_down_cnt}")
                return False

        self.need_stop_up_cnt = 0
        self.need_stop_down_cnt = 0

        return False

    def stop(self, to_zero=False, exit_code=0):
        if self.state == self.STATE_FINISHED:
            return

        self.state = self.STATE_FINISHED

        self.log("Остановка бота...")

        if self.sell_all_on_exit:
            self.sell_all_instruments()

        if self.run_state:
            self.run_state.exit_code = exit_code
            self.run_state.status = RunStatus.FINISHED if not exit_code else RunStatus.FAILED

            account = self.db.get_acc_by_id(self.account_id)
            if account:
                account.balance = self.cur_balance

            self.update_run_state()

    def update_run_state(self):
        state = self.run_state

        if state is None:
            return

        if not state.id:
            db.session.add(state)

        state.updated_at = self.time.now()
        if self.cur_balance:
            state.close = self.cur_balance
            if self.cur_balance > state.high:
                state.high = self.cur_balance
            if self.cur_balance < state.low:
                state.low = self.cur_balance

        if state.open:
            state.profit = round(100 * (state.close - state.open) / state.open, 2)
        state.profit_n = round(1 + state.profit / 100, 4)

        state.data = self.get_status_str()

        state.last_error = f"{self.time.now()} - {self.logger.last_error}" \
            if self.logger.last_error else ''
        state.error_cnt = self.logger.error_cnt

        db.session.commit()

    @staticmethod
    def round(val):
        return round(val, 2)

    def save_balance_to_log(self):
        if self.run_state is None:
            return

        row = AccRunBalance(
            acc_run=self.run_state.id,
            balance=self.cur_balance,
            datetime=self.time.now()
        )
        db.session.add(row)
        db.session.commit()
