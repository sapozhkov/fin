class HistoryOrderType:
    UNKNOWN = 0
    BUY_MARKET = 1
    SELL_MARKET = 2
    OPEN_BUY_LIMIT = 3
    OPEN_SELL_LIMIT = 4
    CANCEL_BUY_LIMIT = 5
    CANCEL_SELL_LIMIT = 6
    EXECUTED_BUY_LIMIT = 7
    EXECUTED_SELL_LIMIT = 8
    BUY_BESTPRICE = 9
    SELL_BESTPRICE = 10
    ORDER_FAIL = 11
    MARK = 12
    MARK_STAR = 13

    EXECUTED_TYPES = {
        BUY_MARKET,
        SELL_MARKET,
        EXECUTED_BUY_LIMIT,
        EXECUTED_SELL_LIMIT,
        BUY_BESTPRICE,
        SELL_BESTPRICE
    }

    VARIANTS = {
        UNKNOWN: ('Unknown', 'black', 'o'),
        BUY_MARKET: ('Market buy', 'black', '^'),
        SELL_MARKET: ('Market sell', 'black', 'v'),
        BUY_BESTPRICE: ('Bestprice buy', 'gray', '^'),
        SELL_BESTPRICE: ('Bestprice sell', 'gray', 'v'),
        OPEN_BUY_LIMIT: ('Limit buy open', 'cyan', 'o'),
        OPEN_SELL_LIMIT: ('Limit sell open', 'red', 'o'),
        CANCEL_BUY_LIMIT: ('Close buy open', 'blue', 'x'),
        CANCEL_SELL_LIMIT: ('Close sell open', 'magenta', 'x'),
        EXECUTED_BUY_LIMIT: ('Limit buy', 'blue', '^'),
        EXECUTED_SELL_LIMIT: ('Limit sell', 'orange', 'v'),
        ORDER_FAIL: ('Order set Fail', 'red', '*'),
        MARK: ('Mark', 'gray', 'o'),
        MARK_STAR: ('Mark Star', 'red', '*'),
    }

    @classmethod
    def get_plot_settings(cls, type_) -> tuple:
        return cls.VARIANTS.get(type_, cls.VARIANTS[cls.UNKNOWN])
