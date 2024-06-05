from app.constants import TaskStatus, TaskType
from app.models import Instrument, Task
from app.tasks import AbstractTask


class UpdInstrumentTask(AbstractTask):
    @staticmethod
    def get_class_task_type() -> int:
        return TaskType.UPD_INSTRUMENT_BASE_CONFIG

    @staticmethod
    def make_name(instrument_id: int) -> str:
        return f"instr_{instrument_id}"

    @classmethod
    def add(cls, instrument_id: int) -> Task | None:
        name = cls.make_name(instrument_id)

        task = Task()
        task.status = TaskStatus.PENDING
        task.type = cls.get_class_task_type()
        task.name = name
        task.data = str(instrument_id)

        if task.already_exists():
            return None

        task.save()
        return task

    @staticmethod
    def run(task: Task) -> bool:
        # достать из базы инструмент
        instrument = Instrument.get_by_id(int(task.data))
        print(instrument)
        # распечатать значение
        return True

