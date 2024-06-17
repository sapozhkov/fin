class AccConfig:
    def __init__(
            self,
            account_id: str = '',
            name='',

            start_time='07:00',  # 10:00
            end_time='15:29',  # 18:29

            stop_up_p=0,
            stop_down_p=0,

            sleep_trading=1 * 60,
    ):
        self.account_id = str(account_id)
        self.name = str(name)

        self.start_time = str(start_time)
        self.end_time = str(end_time)

        # проценты остановки алгоритма при достижении роста и падения
        self.stop_up_p = float(stop_up_p)
        self.stop_down_p = float(stop_down_p)

        self.sleep_trading = int(sleep_trading)

    def __repr__(self):
        stops = f"|u{self.stop_up_p} d{self.stop_down_p}| " \
            if self.stop_up_p or self.stop_down_p else ''
        return f"{self.name} ({self.account_id}) {stops}"

    def to_string(self):
        args = []
        base_conf = AccConfig()
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
        if not isinstance(other, AccConfig):
            raise TypeError
        return (
                self.name == other.name and
                self.account_id == other.account_id and
                self.start_time == other.start_time and
                self.end_time == other.end_time and
                self.sleep_trading == other.sleep_trading and
                self.stop_up_p == other.stop_up_p and
                self.stop_down_p == other.stop_down_p
        )

    def __hash__(self):
        return hash((
            self.name, self.account_id,
            self.start_time, self.end_time,
            self.sleep_trading,
            self.stop_up_p, self.stop_down_p,
        ))
