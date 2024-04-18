import unittest

from dto.config_dto import ConfigDTO


class MyTestCase(unittest.TestCase):
    def test_string_transferring(self):
        config_list = [
            # пустой набор - всё стандартное
            ConfigDTO(),

            # те, что с None взаимодействуют
            ConfigDTO(
                base_shares=None,
                use_shares=3,
            ),

            # полный набор - всё не стандартное. новые поля докидывать сюда
            ConfigDTO(
                start_time='07:13',
                end_time='12:21',

                stop_up_p=.2,
                stop_down_p=.34,

                sleep_trading=30,
                sleep_no_trade=120,

                max_shares=21,
                base_shares=8,
                pretest_period=22,

                majority_trade=False,
                maj_to_zero=False,

                threshold_buy_steps=89,
                threshold_sell_steps=34,

                step_size=12.31,
                step_cnt=9,

                use_shares=6,
            ),
        ]

        for c in config_list:
            self.assertEqual(c, ConfigDTO.from_string(c.to_string()))

    def test_failing(self):
        with self.assertRaises(ValueError):
            ConfigDTO(
                max_shares='hello'
            )


if __name__ == '__main__':
    unittest.main()
