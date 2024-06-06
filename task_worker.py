from app import create_app
from app.constants import TaskStatus
from app.models import Task
from app.tasks import AbstractTask
import importlib


def get_class_from_string(full_class_string):
    module_name, class_name = full_class_string.rsplit('.', 1)
    module = importlib.import_module(module_name)
    cls = getattr(module, class_name)
    return cls


def main():
    # Закрыть таски, работавшие больше дня с ошибкой
    Task.clear_tasks_by_timeout()

    # Выйти, если есть активные задачи
    if Task.has_tasks_in_progress():
        print("Есть активные задачи. Выход.")
        return

    # Взять первую задачу, подходящую по условию
    task = Task.get_next()
    if not task:
        print("Нет задач для выполнения. Выход.")
        return

    # Захватить задачу
    if not task.capture_task():
        print("Не удалось захватить задачу. Выход.")
        return

    # Запустить скрипт обработки (заменить этот комментарий на реальный код)
    print(f"Захвачена задача: {task}")

    try:
        task_class = get_class_from_string(task.class_name)

        if issubclass(task_class, AbstractTask):
            res = task_class.run(task)
            print(f"Задача выполнена {task} с результатом {res}")
        else:
            raise TypeError(f"{task.class_name} не является подклассом AbstractTask")

        task.status = TaskStatus.FINISHED if res else TaskStatus.FAILED
        task.save()
    except Exception as e:
        task.error = str(e)
        task.status = TaskStatus.FAILED
        task.save()

    print(f"Обработка задачи {task} завершена")
    print()


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        main()
