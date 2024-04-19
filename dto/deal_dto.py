from datetime import timezone, datetime
from dateutil import parser


class DealDTO:
    def __init__(self, id_, datetime_, type_, algorithm_name, price, count, commission, total):
        self.id = id_
        self.datetime = datetime_ if isinstance(datetime_, datetime) \
            else parser.parse(datetime_).astimezone(timezone.utc)
        self.type = type_
        self.algorithm_name = algorithm_name
        self.price = price
        self.count = count
        self.commission = commission
        self.total = total

    def __repr__(self):
        return (f"{self.datetime}, "
                f"{self.algorithm_name}, "
                f"{self.total} = {self.count} x ({self.price} - {self.commission}) "
                )
