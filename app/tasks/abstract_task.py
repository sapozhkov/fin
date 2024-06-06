from abc import ABC, abstractmethod

from app.models import Task


class AbstractTask(ABC):

    @abstractmethod
    def add(self, *args, **kwargs) -> Task | None:
        """Добавляет задачу в очередь"""
        pass

    @staticmethod
    @abstractmethod
    def run(task: Task) -> bool:
        pass
