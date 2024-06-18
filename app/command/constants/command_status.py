class CommandStatus:
    NEW = 0
    WORKING = 1
    FINISHED = 2
    EXPIRED = 3
    CANCELED = 4
    FAILED = 5

    @classmethod
    def closed_list(cls):
        return [
            cls.FINISHED,
            cls.EXPIRED,
            cls.CANCELED,
            cls.FAILED,
        ]

    @classmethod
    def get_list(cls):
        return [
            (cls.NEW, 'New'),
            (cls.WORKING, 'Working'),
            (cls.FINISHED, 'Finished'),
            (cls.EXPIRED, 'Expired'),
            (cls.CANCELED, 'Canceled'),
            (cls.FAILED, 'Failed'),
        ]

    @classmethod
    def get_title(cls, status):
        status_dict = dict(cls.get_list())
        return status_dict.get(status, 'Unknown')
