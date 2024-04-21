import os
import sys
import traceback
from signal import *

from dotenv import load_dotenv

from dto.config_dto import ConfigDTO
from lib.trading_bot import TradingBot

load_dotenv()

TOKEN = os.getenv("INVEST_TOKEN")
TICKER = 'RNFT'

if __name__ == '__main__':
    if len(sys.argv) == 1:
        config_dto = ConfigDTO(
            # 19 апр -7д {'profit': 133.8, 'profit_p': 0.1, 'config': 5/-5(2) x l1 x 1.1 ¤, |s6 b0| |u0.0 d0.0| maj+z+ }
            step_max_cnt=5,
            pretest_period=0,
            step_base_cnt=-5,
            step_set_orders_cnt=2,
            step_size=1.1,
            step_lots=2,

            threshold_sell_steps=6,
            threshold_buy_steps=0,

            stop_up_p=0,
            stop_down_p=0,
        )
    else:
        config_dto = ConfigDTO.from_string(sys.argv[1])

    bot = TradingBot(TOKEN, TICKER, config_dto)

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
