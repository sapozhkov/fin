import time
from datetime import datetime, timezone

from bot.env import AbstractTimeHelper


class TimeProdEnvHelper(AbstractTimeHelper):
    def now(self):
        return datetime.now(timezone.utc)

    def sleep(self, seconds):
        time.sleep(seconds)
