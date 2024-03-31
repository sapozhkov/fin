class ConfigDTO:
    def __init__(
            self,
            start_time='07:00',  # 10:00
            end_time='15:29',  # 18:29

            # quit_on_balance_up_percent=2,
            # quit_on_balance_down_percent=1,

            sleep_trading=1 * 60,
            sleep_no_trade=60,

            max_shares=5,
            base_shares=5,
            threshold_buy_steps=6,
            threshold_sell_steps=0,  # вот тут 0 - это важно. эффективность сильно выше. не даем заднюю
            step_size=1.4,
            step_cnt=2,

            use_shares=None,
    ):
        self.start_time = start_time
        self.end_time = end_time

        self.max_shares = max_shares
        self.base_shares = base_shares
        self.threshold_buy_steps = threshold_buy_steps
        self.threshold_sell_steps = threshold_sell_steps
        self.step_size = step_size
        self.step_cnt = step_cnt

        self.sleep_trading = sleep_trading
        self.sleep_no_trade = sleep_no_trade

        # ограничитель количества используемых акций из откупленных. полезно при || запуске на 1 инструмент
        self.use_shares = use_shares

        # предустановленные значения
        self.base_shares = base_shares if base_shares is not None else round(self.max_shares / 2)

        # корректировки параметров
        if self.base_shares > self.max_shares:
            self.base_shares = self.max_shares

        if self.threshold_buy_steps and self.threshold_buy_steps <= self.step_cnt:
            self.threshold_buy_steps = self.step_cnt + 1

        if self.threshold_sell_steps and self.threshold_sell_steps <= self.step_cnt:
            self.threshold_sell_steps = self.step_cnt + 1
