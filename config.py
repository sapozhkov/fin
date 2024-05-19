import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    TOKEN = os.environ.get('INVEST_TOKEN')
    PASSWORD = os.environ.get('PASSWORD')
    DEBUG_MODE = True if os.environ.get('DEBUG') == '1' else False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///db/trading_bot.db'
    # SQLALCHEMY_TRACK_MODIFICATIONS = False
