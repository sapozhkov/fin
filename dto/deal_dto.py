from datetime import timezone
from dateutil import parser


class DealDTO:
    def __init__(self, id_, datetime, type_, algorithm_name, price, commission, total):
        self.id = id_
        self.datetime = parser.parse(datetime).astimezone(timezone.utc)
        self.type = type_
        self.algorithm_name = algorithm_name
        self.price = price
        self.commission = commission
        self.total = total

    def __repr__(self):
        return (f"{self.datetime}, "
                f"{self.algorithm_name}, "
                f"{self.total}, "
                )
