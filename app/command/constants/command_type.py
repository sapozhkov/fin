class CommandType:
    """
    Типы команд для бота
    """

    STOP = 1
    STOP_ON_ZERO = 2
    # BUY = 3
    # CHANGE_STRATEGY = 4
    # CHANGE_CONFIG = 5
    # UPD_COUNTERS = 6

    @classmethod
    def get_list(cls):
        return [
            (cls.STOP, 'Stop'),
            (cls.STOP_ON_ZERO, 'Stop in zero'),
        ]

    @classmethod
    def get_title(cls, status):
        status_dict = dict(cls.get_list())
        return status_dict.get(status, 'Unknown')
