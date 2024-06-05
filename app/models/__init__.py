from .instrument import Instrument  # должен быть выше Deal
from .deal import Deal
from .run import Run
from .user import User
from web import login
from .task import Task


@login.user_loader
def load_user(user_id):
    if user_id == "1":
        return User()
    return None
