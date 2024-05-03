class InstrumentDTO:
    def __init__(self, ticker='', figi='', currency='', round_signs=0, min_increment=0, lot=1, kshort=0):
        self.ticker = ticker
        self.figi = figi
        self.currency = currency
        self.round_signs = int(round_signs)
        self.min_increment = float(min_increment)
        self.lot = int(lot)
        self.kshort = float(kshort)

    def __repr__(self):
        return f"{self.ticker} ({self.figi}), {self.currency}, " \
               f"round_signs={self.round_signs}, inc={self.min_increment}, " \
               f"lot={self.lot}, kshort={self.kshort}"
