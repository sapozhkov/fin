class RunStatus:
    NEW = 1
    SLEEPING = 2
    WORKING = 3
    FINISHED = 4
    FAILED = 5

    _statuses = [
        (NEW, 'New'),
        (SLEEPING, 'Sleeping'),
        (WORKING, 'Working'),
        (FINISHED, 'Finished'),
        (FAILED, 'Failed'),
    ]

    @classmethod
    def get_list(cls):
        return cls._statuses

    @classmethod
    def get_title(cls, status_id):
        status_dict = dict(cls._statuses)
        return status_dict.get(status_id, 'Unknown')
