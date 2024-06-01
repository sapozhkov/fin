import sys
import traceback
from signal import *

from app import create_app, AppConfig
from app.config.run_config import RunConfig
from lib.trading_bot import TradingBot

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        if len(sys.argv) == 1:
            config_dto = RunConfig(
                ticker='RNFT',

                step_max_cnt=5,
                step_base_cnt=0,
                step_set_orders_cnt=3,
                step_size=1.2,
                step_lots=2,

                use_shares=0,

                pretest_period=0,
                pretest_type=RunConfig.PRETEST_NONE,

                threshold_sell_steps=0,
                threshold_buy_steps=6,

                stop_up_p=.05,
                stop_down_p=.15,
            )
        else:
            config_dto = RunConfig.from_string(sys.argv[1])

        bot = TradingBot(AppConfig.TOKEN, config_dto)

        if len(sys.argv) > 1:
            bot.log(f"Config string: {sys.argv[1]}")

        def clean(*_args):
            bot.stop()
            sys.exit(0)

        for sig in (SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM):
            signal(sig, clean)

        try:
            bot.run()
        except Exception as e:
            traceback_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            bot.logger.error(f"Не перехваченное исключение: {e}\nТрассировка: \n{traceback_str}")
            bot.stop()
