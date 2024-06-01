from abc import ABC, abstractmethod


class AbstractLoggerHelper(ABC):
    def __init__(self):
        self.last_message = ''
        self.last_error = ''
        self.error_cnt = 0

    def log(self, message, repeat=False):
        if self.last_message != message or repeat:
            self.info(message)
            self.last_message = message

    @abstractmethod
    def info(self, message):
        pass

    @abstractmethod
    def error(self, message):
        pass

    @abstractmethod
    def debug(self, message):
        pass
