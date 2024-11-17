from typing import Tuple

import pandas as pd

from app import db
from app.command import CommandManager
from app.command.constants import CommandType, CommandStatus
from bot import AbstractBot
from app.config import RunConfig
from app.constants import RunStatus
from app.models import Run, Instrument
from bot.env.prod import TimeProdEnvHelper
from bot.env import AbstractAccountingHelper, AbstractLoggerHelper, AbstractTimeHelper, AbstractProxyClient
from bot.strategy import TradeNormalStrategy, TradeShiftStrategy


class TradingBot(AbstractBot):
    def __init__(
            self,
            config: RunConfig,
            time_helper: AbstractTimeHelper,
            logger_helper: AbstractLoggerHelper,
            client_helper: AbstractProxyClient,
            accounting_helper: AbstractAccountingHelper
    ):
        self.run_state: Run | None = None

        super().__init__(
            config,
            time_helper,
            logger_helper
        )

        self.client = client_helper
        self.accounting = accounting_helper

        if self.config.is_fan_layout():
            self.trade_strategy = TradeShiftStrategy(self)
        else:
            self.trade_strategy = TradeNormalStrategy(self)

        if not self.is_trading_day():
            self.log("Не торговый день. Завершаем работу.")
            self.state = self.STATE_FINISHED
            return

        self.accounting.set_num(self.accounting.get_instrument_count())

        self.trade_strategy.update_start_price_and_counter()

        if not self.validate_and_modify_config():
            self.state = self.STATE_FINISHED
            return

        self.run_state: Run | None = None
        instrument = Instrument.get_by_id(config.instrument_id) if config.instrument_id else None
        if instrument:
            self.run_state = Run(
                instrument=instrument.id,
                date=self.time.now().date(),
                created_at=self.time.now(),
                status=RunStatus.NEW,
                exit_code=0,
                last_error='',
                total=0,
                depo=self.trade_strategy.get_max_start_depo(),
                profit=0,
                expected_profit=instrument.expected_profit,
                data='',
                instrument_data=f"exp profit {instrument.expected_profit}",
                config=str(self.config),
                start_cnt=self.trade_strategy.start_count,
                end_cnt=0,
                open=self.trade_strategy.start_price,
                close=self.trade_strategy.start_price,
                high=self.trade_strategy.start_price,
                low=self.trade_strategy.start_price,
            )

            instrument.price = self.trade_strategy.start_price

            self.update_run_state()

            self.accounting.set_run_id(self.run_state.id)

        self.log(f"INIT \n"
                 f"     config - {self.config}\n"
                 f"     instrument - {self.client.instrument}\n"
                 f"     cur_used_cnt - {self.trade_strategy.start_count}\n"
                 f"     last_price - {self.trade_strategy.start_price}\n"
                 f"     depo - {self.trade_strategy.get_max_start_depo()}\n"
                 f"     instrument_id - {self.config.instrument_id}\n"
                 f"     run_instance - {self.run_state}"
                 )

    def validate_and_modify_config(self) -> bool:
        if self.config.majority_trade and not self.client.instrument.short_enabled_flag:
            self.config.majority_trade = False
            self.logger.error(f"Change majority_trade to False. Instrument short_enabled_flag is False")
            if self.config.step_base_cnt < 0:
                self.config.step_base_cnt = 0
                self.logger.error(f"Change step_base_cnt to 0")

        # приводим лотность к нижнему кратному значению
        inst_lot = self.client.instrument.lot
        if inst_lot > 1:
            self.config.step_lots = inst_lot * (self.config.step_lots // inst_lot)
            if self.config.step_lots == 0:
                self.logger.error('Получена нулевая лотность')
                return False

        # вот тут проводим переустановку base
        self.pretest_and_modify_config()

        return True

    def pretest_and_modify_config(self):
        if not self.config.pretest_period:
            return

        # пока работает только для RSI внутри бота. PRE запускается снаружи до
        if self.config.pretest_type != RunConfig.PRETEST_RSI:
            return

        current_trend = self.get_rsi_trend_val(self.config.pretest_period)
        if current_trend is None:
            return

        if current_trend >= .5:
            self.config.step_base_cnt = self.config.step_max_cnt
        else:
            if self.config.majority_trade:
                self.config.step_base_cnt = -self.config.step_max_cnt
            else:
                self.config.step_base_cnt = 0

        self.log(f"Pretest. RSI = {round(current_trend, 2)}")
        self.log(f"Change step_base_cnt to {self.config.step_base_cnt}")

    def get_rsi_trend_val(self, period) -> float | None:
        to_date = self.time.get_delta_days_date(days=1)
        from_date = self.time.get_delta_days_date(days=period * 2, from_date=to_date)  # Удваиваем период для точности

        candles = self.client.get_day_candles(from_date, to_date)

        closing_prices = pd.Series([self.client.q2f(candle.close) for candle in candles.candles])

        delta = closing_prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 1 - (1 / (1 + rs))
        try:
            current_trend = rsi.iloc[-1]
        except IndexError as err:
            self.logger.error(f'Error while counting RSI: {err}')
            return None

        return current_trend

    def continue_trading(self):
        return self.state != self.STATE_FINISHED

    def run(self):
        while self.continue_trading():
            self.run_iteration()
        self.log('END')

    def can_trade(self) -> Tuple[bool, int]:
        result = super().can_trade()

        if self.client.can_trade():
            return result

        self.logger.error('API сообщил о недоступности торгов, спим')
        return False, self.config.sleep_trading

    def start(self):
        """Начало работы скрипта. первый старт"""

        if self.state != self.STATE_NEW:
            return

        self.state = self.STATE_WORKING

        self.trade_strategy.on_day_start()

        max_portfolio_size = self.trade_strategy.get_max_start_depo()
        if self.run_state:
            self.run_state.depo = max_portfolio_size
            self.run_state.status = RunStatus.WORKING
            self.update_run_state()

    def run_iteration(self):
        self.client.update_cached_status()

        can_trade, sleep_sec = self.can_trade()
        if not can_trade:
            if sleep_sec:
                self.log(f"can not trade, sleep {TimeProdEnvHelper.get_remaining_time_text(sleep_sec)}")
                if self.run_state:
                    self.run_state.status = RunStatus.SLEEPING
                    self.update_run_state()
                self.time.sleep(sleep_sec)
            return

        self.trade_strategy.update_cached_price()

        self.start()

        # Обновляем список активных заявок, тут же заявки на продажу при удачной покупке
        self.trade_strategy.update_orders_status()

        if self.check_bot_commands():
            return

        if self.check_need_stop():
            self.stop(True)
            return

        # закрываем заявки, которые не входят в лимиты
        self.trade_strategy.cancel_orders_by_limits()

        # Выставляем заявки
        self.trade_strategy.place_buy_orders()
        self.trade_strategy.place_sell_orders()

        if self.run_state:
            self.run_state.status = RunStatus.WORKING
            self.update_run_state()

        # self.logger.debug(f"Ждем следующего цикла, sleep {self.config.sleep_trading}")
        self.time.sleep(self.config.sleep_trading)

    def check_need_stop(self):
        if not self.trade_strategy.start_price or not (self.config.stop_up_p or self.config.stop_down_p):
            return False

        profit = self.trade_strategy.get_current_profit()
        max_portfolio = self.trade_strategy.get_max_start_depo()

        need_profit = self.trade_strategy.round(max_portfolio * self.config.stop_up_p)
        if self.config.stop_up_p and profit > need_profit:
            self.log(f"Останавливаем по получению нужного уровня прибыли. "
                     f"profit={profit}, stop_up_p={self.config.stop_up_p}, need_profit={need_profit}")
            return True

        need_loss = self.trade_strategy.round(max_portfolio * self.config.stop_down_p)
        if self.config.stop_down_p and profit < -need_loss:
            self.log(f"Останавливаем по достижению критического уровня потерь. "
                     f"profit={profit}, stop_up_p={self.config.stop_down_p}, need_loss=-{need_loss}")
            return True

        return False

    def stop(self, to_zero=False, exit_code=0):
        if self.state == self.STATE_FINISHED:
            return

        self.state = self.STATE_FINISHED

        self.log("Остановка бота...")
        self.trade_strategy.cancel_active_orders()

        current_count = self.trade_strategy.get_current_count()

        # если надо вернуться в 0 - продать откупленные инструменты
        if to_zero and current_count > 0:
            self.trade_strategy.sell(current_count)

        # при мажоритарной откупить перепроданные, если есть
        if self.config.majority_trade and current_count < 0:
            self.trade_strategy.buy(-current_count)

        current_price = self.trade_strategy.update_cached_price()
        if not current_price:
            self.logger.error("Нулевая цена, статистика НЕ будет верной")

        results = (f"RESULTS\n"
                   f"     config - {self.config}\n"
                   f"     instrument - {self.client.instrument}\n"
                   f"     depo - {self.trade_strategy.get_max_start_depo()}\n"
                   f"     current_price - {current_price}\n"
                   f"     error_cnt - {self.logger.error_cnt}\n"
                   f"     end_cnt - {self.trade_strategy.get_current_count()}\n"
                   f"     total - {self.trade_strategy.get_current_profit()}\n")

        if self.run_state:
            self.run_state.exit_code = exit_code
            self.run_state.status = RunStatus.FINISHED if not exit_code else RunStatus.FAILED

            if self.config.instrument_id:
                instrument = Instrument.get_by_id(self.config.instrument_id)
                if instrument:
                    instrument.price = current_price

            self.update_run_state()

            results += (f"     profit - {self.run_state.profit}\n"
                        f"     profit_n - {self.run_state.profit_n}")

        self.log(results)

    def get_status_str(self) -> str:
        out = f"cur {self.trade_strategy.cached_current_price} | " \
              f"buy {self.trade_strategy.get_existing_buy_order_prices()} " \
              f"sell {self.trade_strategy.get_existing_sell_order_prices()} " \
              f"{self.trade_strategy.get_cur_count_for_log()}"

        if self.run_state:
            out += f"[o{self.run_state.open} " \
                   f"l{self.run_state.low} " \
                   f"h{self.run_state.high} " \
                   f"c{self.run_state.close}]"

        return out

    def update_run_state(self):
        state = self.run_state

        if state is None:
            return
        if not state.id:
            db.session.add(state)

        state.data = self.get_status_str()
        state.total = self.trade_strategy.get_current_profit()
        state.end_cnt = self.trade_strategy.get_current_count()
        if state.depo:
            state.profit = round(100 * state.total / state.depo, 2)
            state.profit_n = round(1 + state.profit / 100, 4)
        state.last_error = f"{self.time.now()} - {self.logger.last_error}" \
            if self.logger.last_error else ''
        state.error_cnt = self.logger.error_cnt
        state.operations_cnt = self.accounting.operations_cnt

        state.updated_at = self.time.now()

        cur_price = self.trade_strategy.cached_current_price
        if cur_price:
            state.close = cur_price
            if cur_price > state.high:
                state.high = cur_price
            if cur_price < state.low:
                state.low = cur_price

        state.updated_at = self.time.now()
        db.session.commit()

    def check_bot_commands(self):
        """
        :return: True если надо прервать выполнение
        """
        if not self.run_state:
            return False

        need_exit = False

        commands = CommandManager.get_new_commands(self.run_state.id)
        for command in commands:
            if command.com_type == CommandType.STOP:
                self.stop()
                CommandManager.update_command_status(command, CommandStatus.FINISHED)
                need_exit = True
            elif command.com_type == CommandType.STOP_ON_ZERO:
                self.stop(to_zero=True)
                CommandManager.update_command_status(command, CommandStatus.FINISHED)
                need_exit = True
            else:
                CommandManager.update_command_status(command, CommandStatus.FAILED)

            self.log(command)

        return need_exit
