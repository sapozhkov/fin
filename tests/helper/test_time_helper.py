import unittest
from datetime import datetime

from app.helper import TimeHelper


class MyTestCase(unittest.TestCase):
    def test_is_weekend(self):
        # пятница - обычный день
        date = datetime.strptime('2024-04-26 06:30', "%Y-%m-%d %H:%M")
        self.assertFalse(TimeHelper.is_weekend(date))

        # рабочая суббота
        date = datetime.strptime('2024-04-27 06:30', "%Y-%m-%d %H:%M")
        self.assertFalse(TimeHelper.is_weekend(date))

        # обычное воскресенье
        date = datetime.strptime('2024-04-28 06:30', "%Y-%m-%d %H:%M")
        self.assertTrue(TimeHelper.is_weekend(date))

        # 1 мая - среда - не работаем
        date = datetime.strptime('2024-05-01 06:30', "%Y-%m-%d %H:%M")
        self.assertTrue(TimeHelper.is_weekend(date))


if __name__ == '__main__':
    unittest.main()
