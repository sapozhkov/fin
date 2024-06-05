from app.constants import TaskType
from app.models import Task


class TaskFactory:
    @staticmethod
    def get_worker(task: Task):
        if task.type == TaskType.UPD_INSTRUMENT_BASE_CONFIG:
            # todo implement
            pass
        else:
            raise ValueError(f"Unknown task type '{task.type}'")
