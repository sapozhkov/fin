class InstrumentDTO:
    def __init__(self, ticker='', figi='', name='', currency='',
                 round_signs=0, min_increment=0, lot=1, short_enabled_flag=False):
        self.ticker = ticker
        self.figi = figi
        self.name = name
        self.currency = currency
        self.round_signs = int(round_signs)
        self.min_increment = float(min_increment)
        self.lot = int(lot)
        self.short_enabled_flag = bool(short_enabled_flag)

    def __repr__(self):
        return f"{self.ticker} / {self.figi}, {self.name}, {self.currency}, " \
               f"round_signs={self.round_signs}, inc={self.min_increment}, " \
               f"lot={self.lot}, short={self.short_enabled_flag}"
