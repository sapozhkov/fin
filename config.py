import os
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    TOKEN = os.environ.get('INVEST_TOKEN')
    PASSWORD = os.environ.get('PASSWORD')
    DEBUG_MODE = True if os.environ.get('DEBUG') == '1' else False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'db', 'db.sqlite')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
