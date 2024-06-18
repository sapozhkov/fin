class TaskStatus:
    PENDING = 0
    IN_PROGRESS = 1
    FINISHED = 2
    FAILED = 3

    @classmethod
    def get_closed_statuses(cls):
        return [cls.FINISHED, cls.FAILED]

    @classmethod
    def get_list(cls):
        return [
            (cls.PENDING, 'Pending'),
            (cls.IN_PROGRESS, 'In progress'),
            (cls.FINISHED, 'Finished'),
            (cls.FAILED, 'Failed'),
        ]

    @classmethod
    def get_title(cls, status):
        status_dict = dict(cls.get_list())
        return status_dict.get(status, 'Unknown')
