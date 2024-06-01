import logging
import os
import sys
from datetime import datetime

from bot.env import AbstractLoggerHelper


class LoggerHelper(AbstractLoggerHelper):
    def __init__(self, name, file_name):
        super().__init__()
        self.logger = logging.getLogger(name)
        self.setup_logger(file_name)

    def setup_logger(self, file_name=''):
        logging.getLogger('tinkoff.invest').setLevel(logging.CRITICAL)

        if not file_name:
            # дефолтное имя - имя запущенного файла без расширения
            file_name = os.path.basename(sys.argv[0]).replace('.py', '')

        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

        # Формируем путь к файлу лога
        log_date = datetime.now().strftime('%Y.%m.%d')
        log_directory = f"./log/{log_date}"
        log_file_path = f"{log_directory}/{file_name}.log"

        # Создаем директорию, если она не существует
        try:
            if not os.path.exists(log_directory):
                os.makedirs(log_directory)
        except FileExistsError:
            # если есть, то её сосед создал, всё ок.
            # 11 пункт дзена
            print(f"directory {log_directory} already exists")

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
        self.last_error = message
        self.error_cnt += 1
        self.logger.error(message)

    def debug(self, message):
        self.logger.debug(message)
