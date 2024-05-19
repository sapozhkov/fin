from flask_login import UserMixin
from app import login


class User(UserMixin):
    id = 1  # Уникальный идентификатор для пользователя


@login.user_loader
def load_user(user_id):
    if user_id == "1":
        return User()
    return None
