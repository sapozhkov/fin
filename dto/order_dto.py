from datetime import datetime, timezone
from dateutil import parser


class OrderDTO:
    def __init__(self, datetime_, type_, price, algorithm_name=''):
        self.datetime = datetime_ if isinstance(datetime_, datetime) \
            else parser.parse(datetime_).astimezone(timezone.utc)
        self.type = type_
        self.price = price
        self.algorithm_name = algorithm_name

    def __repr__(self):
        return (f"{self.datetime}, "
                f"{self.algorithm_name}, "
                f"{self.price}, "
                )
