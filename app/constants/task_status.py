class TaskStatus:
    PENDING = 0
    IN_PROGRESS = 1
    FINISHED = 2
    FAILED = 3

    @classmethod
    def get_closed_statuses(cls):
        return [cls.FINISHED, cls.FAILED]
