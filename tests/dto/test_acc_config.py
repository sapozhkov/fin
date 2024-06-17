import unittest

from app.config import AccConfig


class TestAccConfig(unittest.TestCase):
    def test_string_transferring(self):
        config_list = [
            # пустой набор - всё стандартное
            AccConfig(),

            # полный набор - всё не стандартное. новые поля докидывать сюда
            AccConfig(
                account_id='123213',
                name='hello',

                start_time='07:13',
                end_time='12:21',

                stop_up_p=.2,
                stop_down_p=.34,

                sleep_trading=30,
            ),
        ]

        for c in config_list:
            self.assertEqual(c, AccConfig.from_string(c.to_string()))

    # падение с ошибкой при наличии левых параметров.
    # пусть сразу завалится и высветит, чем будет работать не пойми как
    def test_additional_string_parameters(self):
        with self.assertRaises(TypeError):
            config = AccConfig(
                stop_up_p=.2,
                stop_down_p=.34,
            )

            to_string = config.to_string()
            AccConfig.from_string(to_string + ',qwe=321,a=,de=123')

    def test_qe_fail(self):
        with self.assertRaises(TypeError):
            c = AccConfig()
            a = []
            return c == a

    def test_hash(self):
        configs = [
            AccConfig(stop_up_p=3),
            AccConfig(stop_up_p=2),
            AccConfig(stop_up_p=3),
        ]
        unique_configs = set(configs)
        self.assertEqual(len(unique_configs), 2)

    def test_eq_method_uses_all_fields(self):
        method_code = AccConfig.__eq__.__code__
        fields = vars(AccConfig())
        for field in fields:
            self.assertIn(field, method_code.co_names,
                          f"Field '{field}' is not used in __eq__ method")

    def test_hash_method_uses_all_fields(self):
        method_code = AccConfig.__hash__.__code__
        fields = vars(AccConfig())
        for field in fields:
            self.assertIn(field, method_code.co_names,
                          f"Field '{field}' is not used in __hash__ method")


if __name__ == '__main__':
    unittest.main()
