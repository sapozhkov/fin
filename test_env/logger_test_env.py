from prod_env.logger_helper import AbstractLoggerHelper
from test_env.time_test_env import TimeTestEnvHelper


class LoggerTestEnvHelper(AbstractLoggerHelper):
    def __init__(self, time_helper: TimeTestEnvHelper, do_printing=True):
        super().__init__()
        self.time = time_helper
        self.do_printing = do_printing

    def info(self, message):
        if not self.do_printing:
            return
        time = self.time.current_time
        print(f"{time.strftime('%H:%M')} - {message}")

    def error(self, message):
        self.last_error = message
        self.error_cnt += 1
        self.info(message)

    def debug(self, message):
        self.info(message)
