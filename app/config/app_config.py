import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Определяем путь к .env файлу
dotenv_path = os.path.join(basedir, '.env')
load_dotenv(dotenv_path)


class AppConfig:
    BASE_DIR = basedir
    """Базовая директория (корень) проекта"""

    TOKEN = os.environ.get('INVEST_TOKEN')
    """Токен доступа к Tinkoff Invest API."""

    PASSWORD = os.environ.get('PASSWORD')
    """Пароль для доступа в админку"""

    DEBUG_MODE = True if os.environ.get('DEBUG') == '1' else False
    """флаг дебаг режима админки"""

    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    """ключ для генерации cookies админки """

    SESSION_TYPE = 'filesystem'
    """это для того, чтобы авторизация на мобилке не отваливалась"""

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(basedir, 'db', 'db.sqlite'))
    """реквизиты доступа к базе данных"""

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    INSTRUMENT_ON_THRESHOLD = float(os.environ.get('INSTRUMENT_ON_THRESHOLD', 0.1))
    """% профита, на котором инструмент активируется после ежедневного теста (средний дневной уровень)"""

    ACC_BALANCE_CORRECTION = float(os.environ.get('ACC_BALANCE_CORRECTION', 0.95))
    """
    какую часть баланса аккаунта использовать в торговле. 1 ничего не меняем, 0.9 - -10%, 2 - х2 для мажоритарной,
    а можно выставить 0.2 и мы будем оперировать только 20% баланса, чтобы не потерять слишком много, например
    """

    ALLOWED_ORDER_RANGE = 0.05
    """
    допустимый диапазон выставления заявок от текущей цены (±5%)
    """

    TIME_SHIFT_HOURS = 3
    """
    Сдвиг временной зоны при выводе данных 
    """

    MAX_MEMORY_FOR_SCRIPT = int(os.environ.get('MAX_MEMORY_FOR_SCRIPT', 130))
    """Максимальный объем памяти, выделенный под скрипт"""

    MEMORY_RUN_COEFFICIENT = float(os.environ.get('MEMORY_RUN_COEFFICIENT', 0.7))
    """Модификатор объема памяти. На сколько меньше считать объем скрипта при первичном запуске"""
