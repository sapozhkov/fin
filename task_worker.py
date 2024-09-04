import random
import traceback
from datetime import datetime

from app import create_app
from app.constants import TaskStatus
from app.models import Task
from app.tasks import AbstractTask
import importlib


def main():

    def get_class_from_string(full_class_string):
        module_name, class_name = full_class_string.rsplit('.', 1)
        module = importlib.import_module(module_name)
        cls = getattr(module, class_name)
        return cls

    def print_log(text=''):
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {text}" if text else '')

    # Выйти, если есть активные задачи
    if Task.has_tasks_in_progress():
        return

    # Взять первую задачу, подходящую по условию
    task = Task.get_next()
    if not task:
        return

    # Захватить задачу
    if not task.capture_task():
        print_log("Не удалось захватить задачу. Выход.")
        return

    # Запустить скрипт обработки (заменить этот комментарий на реальный код)
    print_log(f"Захвачена задача: {task}")

    try:
        task_class = get_class_from_string(task.class_name)

        if issubclass(task_class, AbstractTask):
            res = task_class.run(task)
            print_log(f"Задача выполнена {task} с результатом {res}")
        else:
            raise TypeError(f"{task.class_name} не является подклассом AbstractTask")

        task.status = TaskStatus.FINISHED if res else TaskStatus.FAILED
        task.save()
    except Exception as e:
        traceback_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
        print_log(f"Исключение при выполнении задачи: {e}\nТрассировка: \n{traceback_str}")

        task.error = str(e)
        task.status = TaskStatus.FAILED
        task.save()

    print_log(f"Обработка задачи {task} завершена")
    print_log()


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        main()
