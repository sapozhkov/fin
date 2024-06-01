import unittest

from app.config.run_config import RunConfig


class MyTestCase(unittest.TestCase):
    def test_string_transferring(self):
        config_list = [
            # пустой набор - всё стандартное
            RunConfig(),

            # те, что с None взаимодействуют
            RunConfig(
                step_base_cnt=None,
                use_shares=3,
            ),

            # полный набор - всё не стандартное. новые поля докидывать сюда
            RunConfig(
                start_time='07:13',
                end_time='12:21',

                stop_up_p=.2,
                stop_down_p=.34,

                sleep_trading=30,
                sleep_no_trade=120,

                step_max_cnt=21,
                step_base_cnt=8,

                pretest_type=RunConfig.PRETEST_RSI,
                pretest_period=22,

                majority_trade=False,

                threshold_buy_steps=89,
                threshold_sell_steps=34,

                step_size=12.31,
                step_set_orders_cnt=9,
                step_lots=2,

                use_shares=6,
            ),
        ]

        for c in config_list:
            self.assertEqual(c, RunConfig.from_string(c.to_string()))

    # падение с ошибкой при наличии левых параметров.
    # пусть сразу завалится и высветит, чем будет работать не пойми как
    def test_additional_string_parameters(self):
        with self.assertRaises(TypeError):
            config = RunConfig(
                stop_up_p=.2,
                stop_down_p=.34,
            )

            to_string = config.to_string()
            RunConfig.from_string(to_string + ',qwe=321,a=,de=123')

    def test_param_modify(self):

        config_normal = RunConfig(
            step_max_cnt=5,
            step_base_cnt=2,
        )
        config_none = RunConfig(
            step_max_cnt=5,
            step_base_cnt=None,
        )

        self.assertEqual(config_normal, config_none)
        self.assertEqual(str(config_normal), str(config_none))

        config_max = RunConfig(
            step_max_cnt=5,
            step_base_cnt=7,
            step_set_orders_cnt=5,
            threshold_buy_steps=5,
            threshold_sell_steps=5,

        )
        config_over = RunConfig(
            step_max_cnt=5,
            step_base_cnt=5,
            step_set_orders_cnt=5,
            threshold_buy_steps=2,
            threshold_sell_steps=2,
        )

        self.assertEqual(config_max, config_over)

    def test_failing(self):
        with self.assertRaises(ValueError):
            RunConfig(
                step_max_cnt='hello'
            )

    def test_qe_fail(self):
        with self.assertRaises(TypeError):
            c = RunConfig()
            a = []
            return c == a

    def test_hash(self):
        configs = [
            RunConfig(step_max_cnt=3),
            RunConfig(step_max_cnt=2),
            RunConfig(step_max_cnt=3),
        ]
        unique_configs = set(configs)
        self.assertEqual(len(unique_configs), 2)

    def test_eq_method_uses_all_fields(self):
        method_code = RunConfig.__eq__.__code__
        fields = vars(RunConfig())
        for field in fields:
            self.assertIn(field, method_code.co_names,
                          f"Field '{field}' is not used in __eq__ method")

    def test_hash_method_uses_all_fields(self):
        method_code = RunConfig.__hash__.__code__
        fields = vars(RunConfig())
        for field in fields:
            self.assertIn(field, method_code.co_names,
                          f"Field '{field}' is not used in __hash__ method")

    def test_from_repr_string(self):
        """
        восстановление из repr строки работает не для всех полей
        RNFT 3/0/3 x l2 x 1.0¤, |s0 b0| |u0.0 d0.0| maj+z+

        вот всё, чего тут нет и не работает
        """

        config_list = [
            # пустой набор - всё стандартное
            RunConfig(),

            RunConfig(pretest_period=0),
            RunConfig(ticker="TEST"),
            RunConfig(step_base_cnt=-3),

            # те, что с None взаимодействуют
            RunConfig(
                step_base_cnt=None,
            ),

            # разные варианты претестов
            RunConfig(
                pretest_type=RunConfig.PRETEST_NONE,
                pretest_period=12,
            ),

            RunConfig(
                pretest_type=RunConfig.PRETEST_RSI,
                pretest_period=13,
            ),

            RunConfig(
                pretest_type=RunConfig.PRETEST_PRE,
                pretest_period=14,
            ),

            # # полный набор - всё не стандартное. новые поля докидывать сюда
            RunConfig(
                ticker='TEST',

                stop_up_p=.2,
                stop_down_p=.34,

                step_max_cnt=21,
                step_base_cnt=8,
                pretest_type=RunConfig.PRETEST_RSI,
                pretest_period=22,

                majority_trade=False,

                threshold_buy_steps=89,
                threshold_sell_steps=34,

                step_size=12.31,
                step_set_orders_cnt=9,
                step_lots=2,
            ),
        ]

        for c in config_list:
            self.assertEqual(c, RunConfig.from_repr_string(str(c)), str(c))
            self.assertEqual(c, RunConfig.from_repr_string(str(c).strip()), f"'{str(c).strip()}'")


if __name__ == '__main__':
    unittest.main()
