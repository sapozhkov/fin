from abc import ABC, abstractmethod

from app.constants import TaskStatus
from app.models import Task


class AbstractTask(ABC):
    @staticmethod
    @abstractmethod
    def get_class_task_type() -> int:
        """Отдает уникальный идентификатор из TaskType"""
        pass

    @abstractmethod
    def add(self, *args, **kwargs) -> Task | None:
        """Добавляет задачу в очередь"""
        pass

    @staticmethod
    @abstractmethod
    def run(task: Task) -> bool:
        pass

    @classmethod
    def execute_task(cls, task: Task) -> bool:
        if task.status != TaskStatus.PENDING:
            return False

        task.status = TaskStatus.IN_PROGRESS
        task.save()

        res = False
        try:
            res = cls.run(task)
            task.status = TaskStatus.FINISHED if res else TaskStatus.FAILED
            task.save()
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
            task.save()

        return res
