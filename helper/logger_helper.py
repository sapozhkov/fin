import logging
import os
import sys
from abc import ABC, abstractmethod
from datetime import datetime


class AbstractLoggerHelper(ABC):
    def __init__(self):
        self.logger_last_message = ''

    def log(self, message, repeat=False):
        if self.logger_last_message != message or repeat:
            self.info(message)
            self.logger_last_message = message

    @abstractmethod
    def info(self, message):
        pass

    @abstractmethod
    def error(self, message):
        pass

    @abstractmethod
    def debug(self, message):
        pass


class LoggerHelper(AbstractLoggerHelper):
    def __init__(self, name):
        super().__init__()
        self.logger = logging.getLogger(name)
        self.setup_logger()

    def setup_logger(self):
        logging.getLogger('tinkoff.invest').setLevel(logging.CRITICAL)

        # Получаем имя запущенного файла без расширения
        file_name = os.path.basename(sys.argv[0]).replace('.py', '')

        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

        # Формируем путь к файлу лога
        log_date = datetime.now().strftime('%Y.%m.%d')
        log_directory = f"./log/{log_date}"
        log_file_path = f"{log_directory}/{file_name}.log"

        # Создаем директорию, если она не существует
        if not os.path.exists(log_directory):
            os.makedirs(log_directory)

        # Создаем логгер
        self.logger.setLevel(logging.INFO)

        # Формат сообщений логгера
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # Создаем и настраиваем обработчик для записи в файл
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def info(self, message):
        self.logger.info(message)

    def error(self, message):
        self.logger.error(message)

    def debug(self, message):
        self.logger.debug(message)
