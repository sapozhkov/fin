from datetime import timedelta

from helper.time_helper import AbstractTimeHelper


class TimeTestEnvHelper(AbstractTimeHelper):
    def __init__(self, now):
        super().__init__()
        self.current_time = now
        self.sleep_until = now

    def now(self):
        return self.current_time

    def sleep(self, seconds):
        self.sleep_until = self.current_time + timedelta(seconds=seconds)

    def set_time(self, new_time):
        self.current_time = new_time

    def is_time_to_awake(self):
        return self.current_time >= self.sleep_until
