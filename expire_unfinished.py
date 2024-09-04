from app import create_app
from app.command import CommandManager
from app.models import Run, AccRun, Task


def main():
    CommandManager.expire_unfinished_commands()
    Run.expire_unfinished()
    AccRun.expire_unfinished()
    Task.clear_tasks_by_timeout()


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        main()
