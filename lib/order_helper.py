class OrderHelper:
    UNKNOWN = 0
    OPEN_BUY_MARKET = 1
    OPEN_SELL_MARKET = 2
    OPEN_BUY_LIMIT = 3
    OPEN_SELL_LIMIT = 4
    CANCEL_BUY_LIMIT = 5
    CANCEL_SELL_LIMIT = 6

    VARIANTS = {
        UNKNOWN: ('Unknown', 'black', 'o'),
        OPEN_BUY_MARKET: ('Market buy', 'orange', '^'),
        OPEN_SELL_MARKET: ('Market sell', 'blue', 'v'),
        OPEN_BUY_LIMIT: ('Limit buy open', 'green', 'o'),
        OPEN_SELL_LIMIT: ('Limit sell open', 'red', 'o'),
        CANCEL_BUY_LIMIT: ('Close buy open', 'green', 'x'),
        CANCEL_SELL_LIMIT: ('Close sell open', 'red', 'x'),
    }

    @classmethod
    def get_plot_settings(cls, type_) -> tuple:
        return cls.VARIANTS.get(type_, cls.VARIANTS[cls.UNKNOWN])
