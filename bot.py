import sys
import traceback
from signal import *

from app import create_app
from app.config import RunConfig
from app.models import Instrument
from bot import TradingBot
from bot.env.prod import TimeProdEnvHelper, LoggerHelper, TinkoffProxyClient, AccountingHelper

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

                step_size_shift=0.2,
                majority_trade=True,

                stop_up_p=.05,
                stop_down_p=.15,

                instrument_id=4,
            )
        else:
            config_dto = RunConfig.from_string(sys.argv[1])

        instrument = None
        account_id = ''
        if config_dto.instrument_id:
            instrument = Instrument.get_by_id(config_dto.instrument_id)
            if instrument:
                account_id = str(instrument.account)

        log_name = config_dto.name or config_dto.ticker
        if instrument:
            log_name = f"{instrument.account_rel.name}_{log_name}"

        time_helper = TimeProdEnvHelper()
        logger_helper = LoggerHelper(__name__, log_name)
        client_helper = TinkoffProxyClient(config_dto.ticker, time_helper, logger_helper, account_id)
        accounting_helper = AccountingHelper(__file__, client_helper)

        bot = TradingBot(
            config=config_dto,
            time_helper=time_helper,
            logger_helper=logger_helper,
            client_helper=client_helper,
            accounting_helper=accounting_helper,
        )

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
