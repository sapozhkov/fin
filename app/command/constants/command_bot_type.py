class CommandBotType:
    TRADE_BOT = 1
    ACC_BOT = 2

    @classmethod
    def get_list(cls):
        return [
            (cls.TRADE_BOT, 'Trade bot'),
            (cls.ACC_BOT, 'Account bot'),
        ]

    @classmethod
    def get_title(cls, status):
        status_dict = dict(cls.get_list())
        return status_dict.get(status, 'Unknown')
