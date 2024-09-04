from app import create_app
from app.command import CommandManager


def main():
    CommandManager.expire_unfinished_commands()


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        main()
