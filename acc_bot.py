import sys
import traceback
from signal import *

from app import create_app
from app.config import AccConfig
from bot import TradingAccountBot

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        if len(sys.argv) == 1:
            acc_config = AccConfig(
                name='test',
                account_id='2139186563',

                stop_up_p=.05,
                stop_down_p=.15,
            )
        else:
            acc_config = AccConfig.from_string(sys.argv[1])

        bot = TradingAccountBot(acc_config)

        if len(sys.argv) > 1:
            bot.log(f"Config string: {sys.argv[1]}")

        def clean(*_args):
            bot.stop(exit_code=1)
            sys.exit(0)

        for sig in (SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM):
            signal(sig, clean)

        try:
            bot.run()
        except Exception as e:
            traceback_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            bot.logger.error(f"Не перехваченное исключение: {e}\nТрассировка: \n{traceback_str}")
            bot.stop(exit_code=2)
