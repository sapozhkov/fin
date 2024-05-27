class RunStatus:
    _statuses = [
        (1, 'New'),
        (2, 'Sleeping'),
        (3, 'Working'),
        (4, 'Finished'),
        (5, 'Failed'),
    ]

    @classmethod
    def get_list(cls):
        return cls._statuses

    @classmethod
    def get_title(cls, status_id):
        status_dict = dict(cls._statuses)
        return status_dict.get(status_id, 'Unknown')
