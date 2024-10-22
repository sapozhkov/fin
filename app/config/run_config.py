import re


class RunConfig:
    PRETEST_NONE = ''
    PRETEST_RSI = 'rsi'  # прогон по RSI
    PRETEST_PRE = 'pre'  # анализ и выбор лучшего варианта том же алгоритме за pretest_period дней с вариациями конфига
    PRETEST_FAN = 'fan'  # веерная раскладка, она же нелинейный шаг

    MIN_MAJ_MAX_CNT = 2
    MIN_NON_MAJ_MAX_CNT = 4

    def __init__(
            self,
            name='',
            ticker='',
            instrument_id=0,

            start_time='07:00',  # 10:00
            end_time='15:29',  # 18:29

            stop_up_p=0,
            stop_down_p=0,

            sleep_trading=1 * 60,

            pretest_type=PRETEST_NONE,
            pretest_period=0,

            majority_trade=False,

            threshold_buy_steps=0,
            threshold_sell_steps=0,

            step_max_cnt=0,
            step_base_cnt=0,
            step_size=0,
            step_set_orders_cnt=0,
            step_lots=0,
            step_size_shift=0,
    ):
        self.name = str(name)
        self.ticker = str(ticker)
        self.instrument_id = int(instrument_id)

        self.start_time = str(start_time)
        self.end_time = str(end_time)

        self.step_max_cnt = int(step_max_cnt)
        self.step_base_cnt = int(step_base_cnt) if step_base_cnt is not None else None

        self.step_size = float(step_size)
        self.step_set_orders_cnt = int(step_set_orders_cnt)
        self.step_lots = int(step_lots)
        self.step_size_shift = float(step_size_shift)

        self.pretest_type = str(pretest_type)
        self.pretest_period = int(pretest_period)

        self.majority_trade = bool(majority_trade)
        self.threshold_buy_steps = int(threshold_buy_steps)
        self.threshold_sell_steps = int(threshold_sell_steps)

        # проценты остановки алгоритма при достижении роста и падения
        self.stop_up_p = float(stop_up_p)
        self.stop_down_p = float(stop_down_p)

        self.sleep_trading = int(sleep_trading)

        # предустановленные значения
        if self.step_base_cnt is None:
            self.step_base_cnt = round(self.step_max_cnt / 2)

        # корректировки параметров
        if self.is_maj_trade():
            if self.step_max_cnt < self.MIN_MAJ_MAX_CNT:
                self.step_max_cnt = self.MIN_MAJ_MAX_CNT
        else:
            if self.step_max_cnt < self.MIN_NON_MAJ_MAX_CNT:
                self.step_max_cnt = self.MIN_NON_MAJ_MAX_CNT

        if self.step_size <= 0:
            self.step_size = 0.2

        if self.pretest_type not in [self.PRETEST_NONE, self.PRETEST_RSI, self.PRETEST_PRE, self.PRETEST_FAN]:
            self.pretest_type = self.PRETEST_NONE

        # todo вот это чекнуть
        # if self.pretest_type == self.PRETEST_NONE:
        #     self.pretest_period = 0

        if self.step_base_cnt > self.step_max_cnt:
            self.step_base_cnt = self.step_max_cnt

        min_base_cnt = -self.step_max_cnt if self.majority_trade else 0
        if self.step_base_cnt < min_base_cnt:
            self.step_base_cnt = min_base_cnt

        if self.step_set_orders_cnt > self.step_max_cnt:
            self.step_set_orders_cnt = self.step_max_cnt

        if self.threshold_buy_steps and self.threshold_buy_steps <= self.step_set_orders_cnt:
            self.threshold_buy_steps = self.step_set_orders_cnt + 1

        if self.threshold_sell_steps and self.threshold_sell_steps <= self.step_set_orders_cnt:
            self.threshold_sell_steps = self.step_set_orders_cnt + 1

        if self.step_lots <= 0:
            self.step_lots = 1

    def is_maj_trade(self):
        return self.majority_trade

    def is_fan_layout(self):
        return self.pretest_type == self.PRETEST_FAN

    def __repr__(self):
        base = f"{self.pretest_type}{self.pretest_period}:{self.step_base_cnt}" \
            if self.pretest_type or self.pretest_period else f"{self.step_base_cnt}"
        thresholds = f"|s{self.threshold_sell_steps} b{self.threshold_buy_steps}| " \
            if self.threshold_sell_steps or self.threshold_buy_steps else ''
        stops = f"|u{self.stop_up_p} d{self.stop_down_p}| " \
            if self.stop_up_p or self.stop_down_p else ''
        step_shift = f"(+x{self.step_size_shift})" if self.step_size_shift else ''
        return (f"{self.ticker}{'+' if self.majority_trade else '-'} "
                f"{self.step_max_cnt}/{base}/{self.step_set_orders_cnt} "
                f"x l{self.step_lots} x {self.step_size}{step_shift}¤ "
                f"{thresholds}{stops}"
                )

    @classmethod
    def from_repr_string(cls, input_string) -> 'RunConfig':
        # RNFT+ 3/0/3 x l2 x 1.0¤ |s0 b0| |u0.0 d0.0| maj+z+
        # RNFT- 3/pre7:-3/3 x l2 x 1.0¤ |s0 b0| |u0.0 d0.0| maj+z+
        # RNFT- 3/pre7:-3/3 x l2 x 1.0¤
        # RNFT- 3/pre7:-3/3 x l2 x 1.0(+x0.1)¤
        pattern = r"^\s*(?P<ticker>\w*)(?P<majority_trade>[\+\-]) " \
                  r"(?P<step_max_cnt>\d+)/" \
                  r"((?P<pretest_type>pre|rsi|fan))?((?P<pretest_period>\d+))?\:?(?P<step_base_cnt>-?\d+)/" \
                  r"(?P<step_set_orders_cnt>\d+) " \
                  r"x l(?P<step_lots>\d+) x (?P<step_size>[\d.]+)(\(\+x(?P<step_size_shift>[\d.]+)\))?¤\s?" \
                  r"(\|s(?P<threshold_sell_steps>\d+) b(?P<threshold_buy_steps>\d+)\|\s?)?" \
                  r"(\|u(?P<stop_up_p>[\d.]+) d(?P<stop_down_p>[\d.]+)\|\s?)?$"
        match = re.match(pattern, input_string)

        if match:
            values = match.groupdict()
            # Преобразование строковых значений в нужный формат (int, float, bool и т.д.)
            values['ticker'] = str(values['ticker'] or '')
            values['step_max_cnt'] = int(values['step_max_cnt'])
            values['step_base_cnt'] = int(values['step_base_cnt'])
            values['step_set_orders_cnt'] = int(values['step_set_orders_cnt'])
            values['pretest_type'] = str(values['pretest_type'] or '')
            values['pretest_period'] = int(values['pretest_period'] or 0)
            values['step_lots'] = int(values['step_lots'])
            values['step_size'] = float(values['step_size'])
            values['step_size_shift'] = float(values['step_size_shift'] or 0)
            values['threshold_sell_steps'] = int(values['threshold_sell_steps'] or 0)
            values['threshold_buy_steps'] = int(values['threshold_buy_steps'] or 0)
            values['stop_up_p'] = float(values['stop_up_p'] or 0)
            values['stop_down_p'] = float(values['stop_down_p'] or 0)
            values['majority_trade'] = values['majority_trade'] == '+'

            return RunConfig(**values)
        else:
            raise ValueError(f"Cannot create RunConfig from string '{input_string}'")

    def to_string(self):
        args = []
        base_conf = RunConfig()
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
        if config_string == '':
            return cls()

        args = config_string.split(',')

        d = dict()
        for arg_str in args:
            key, value = arg_str.split('=')
            d[key] = value

        return cls(**d)

    def __eq__(self, other):
        if not isinstance(other, RunConfig):
            raise TypeError(f"{other} is not instance of RunConfig")
        return (
                self.name == other.name and
                self.ticker == other.ticker and
                self.instrument_id == other.instrument_id and
                self.start_time == other.start_time and
                self.end_time == other.end_time and
                self.sleep_trading == other.sleep_trading and
                self.step_max_cnt == other.step_max_cnt and
                self.step_base_cnt == other.step_base_cnt and
                self.pretest_type == other.pretest_type and
                self.pretest_period == other.pretest_period and
                self.majority_trade == other.majority_trade and
                self.threshold_buy_steps == other.threshold_buy_steps and
                self.stop_up_p == other.stop_up_p and
                self.stop_down_p == other.stop_down_p and
                self.threshold_sell_steps == other.threshold_sell_steps and
                self.step_size == other.step_size and
                self.step_set_orders_cnt == other.step_set_orders_cnt and
                self.step_lots == other.step_lots and
                self.step_size_shift == other.step_size_shift
        )

    def __hash__(self):
        return hash((
            self.name, self.ticker, self.instrument_id,
            self.start_time, self.end_time,
            self.sleep_trading,
            self.step_max_cnt, self.step_base_cnt,
            self.pretest_type, self.pretest_period,
            self.majority_trade,
            self.threshold_buy_steps, self.threshold_sell_steps,
            self.stop_up_p, self.stop_down_p,
            self.step_size, self.step_set_orders_cnt, self.step_lots, self.step_size_shift,
        ))
