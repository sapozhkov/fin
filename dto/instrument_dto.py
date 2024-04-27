class InstrumentDTO:
    # todo 76 26 протестировать разные варианты. в тч и сбер, где корявая градация или поискать 0.5
    def __init__(self, ticker='', figi='', currency='', round_signs=0, min_increment=0, lot=1):
        self.ticker = ticker
        self.figi = figi
        self.currency = currency
        self.round_signs = int(round_signs)
        self.min_increment = float(min_increment)
        self.lot = int(lot)

    def __repr__(self):
        return f"InstrumentDTO({self.ticker} ({self.figi}), {self.currency}, " \
               f"round_signs={self.round_signs}, min_increment={self.min_increment}, lot={self.lot}"
