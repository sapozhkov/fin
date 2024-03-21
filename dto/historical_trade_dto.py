class HistoricalTradeDTO:
    def __init__(
            self,
            date,
            alg_name,
            total,
            cnt,
            is_closed
    ):
        self.date = date
        self.alg_name = alg_name
        self.total = round(total, 2)
        self.cnt = cnt
        self.is_closed = is_closed
