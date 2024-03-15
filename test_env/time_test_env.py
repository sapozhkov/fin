from datetime import timedelta

from helper.time_helper import AbstractTime


class TimeTestEnv(AbstractTime):
    def __init__(self, now):
        self.current_time = now
        self.sleep_until = now

    def now(self):
        return self.current_time

    def sleep(self, seconds):
        self.sleep_until = self.current_time + timedelta(seconds=seconds)

    def set_time(self, time):
        self.current_time = time

    def is_time_to_awake(self):
        return self.current_time >= self.sleep_until
