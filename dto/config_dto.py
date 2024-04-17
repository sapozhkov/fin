class ConfigDTO:
    def __init__(
            self,
            start_time='07:00',  # 10:00
            end_time='15:29',  # 18:29

            # quit_on_balance_up_percent=2,
            # quit_on_balance_down_percent=1,

            sleep_trading=1 * 60,
            sleep_no_trade=1 * 60,

            max_shares=5,
            base_shares=5,
            pretest_period=13,

            majority_trade=True,
            maj_to_zero=True,  # откупить до 0 в конце работы алгоритма (или дня)

            threshold_buy_steps=6,
            threshold_sell_steps=0,  # вот тут 0 - это важно. эффективность сильно выше. не даем заднюю

            step_size=1.4,
            step_cnt=5,

            use_shares=None,
    ):
        self.start_time = start_time
        self.end_time = end_time

        self.max_shares = int(max_shares)
        self.base_shares = int(base_shares) if base_shares is not None else None
        self.pretest_period = int(pretest_period)
        self.majority_trade = bool(majority_trade)
        self.maj_to_zero = bool(maj_to_zero)
        self.threshold_buy_steps = int(threshold_buy_steps)
        self.threshold_sell_steps = int(threshold_sell_steps)
        self.step_size = float(step_size)
        self.step_cnt = int(step_cnt)

        self.sleep_trading = int(sleep_trading)
        self.sleep_no_trade = int(sleep_no_trade)

        # ограничитель количества используемых акций из откупленных. полезно при || запуске на 1 инструмент
        self.use_shares = int(use_shares) if use_shares is not None and use_shares != '' else None

        # предустановленные значения
        if self.base_shares is None:
            self.base_shares = round(self.max_shares / 2)

        # корректировки параметров
        if self.base_shares > self.max_shares:
            self.base_shares = self.max_shares

        if self.threshold_buy_steps and self.threshold_buy_steps <= self.step_cnt:
            self.threshold_buy_steps = self.step_cnt + 1

        if self.threshold_sell_steps and self.threshold_sell_steps <= self.step_cnt:
            self.threshold_sell_steps = self.step_cnt + 1

    def __repr__(self):
        base = f"pre{self.pretest_period}" if self.pretest_period else f"{self.base_shares}"
        return (f"{self.max_shares}/{base}({self.step_cnt}) x {self.step_size} rub, "
                f"|s{self.threshold_sell_steps} b{self.threshold_buy_steps}| "
                f"maj{'+' if self.majority_trade else '-'}z{'+' if self.maj_to_zero else '-'} "
                )

    def to_string(self):
        args = []
        base_conf = ConfigDTO()
        for key, value in self.__dict__.items():
            if value != base_conf.__dict__[key]:
                if value is None:
                    value = ''
                elif isinstance(value, bool) and not value:
                    value = ''
                args.append(f'{key}={value}')
        return ','.join(args)

    @classmethod
    def from_string(cls, config_string):
        args = config_string.split(',')

        d = dict()
        for arg_str in args:
            key, value = arg_str.split('=')
            d[key] = value

        return cls(**d)
