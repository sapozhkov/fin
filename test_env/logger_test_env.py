from helper.logger_helper import AbstractLoggerHelper
from test_env.time_test_env import TimeTestEnvHelper


class LoggerTestEnvHelper(AbstractLoggerHelper):
    def __init__(self, time_helper: TimeTestEnvHelper):
        super().__init__()
        self.time = time_helper

    def info(self, message):
        time = self.time.current_time
        print(f"{time.hour + self.time.tmz}{time.strftime(":%M")} - {message}")

    def error(self, message):
        self.info(message)

    def debug(self, message):
        self.info(message)
