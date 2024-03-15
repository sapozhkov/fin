class Config:
    def __init__(self, profit_percent, stop_loss_percent, candles_count):

        self.commission = 0.0005
        self.profit_percent = profit_percent / 100
        self.stop_loss_percent = stop_loss_percent / 100

        self.candles_count = candles_count

        self.no_operation_timeout_seconds = 300

        self.sleep_no_trade = 60
        self.sleep_trading = 300
