import unittest

from app.config import AccConfig


class TestAccConfig(unittest.TestCase):
    def test_string_transferring(self):
        config_list = [
            # пустой набор - всё стандартное
            AccConfig(
                account_id='1234568',
                name="test acc",
            ),

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
                account_id='1234568',
                name="test acc",

                stop_up_p=.2,
                stop_down_p=.34,
            )

            to_string = config.to_string()
            AccConfig.from_string(to_string + ',qwe=321,a=,de=123')

    def test_qe_fail(self):
        with self.assertRaises(TypeError):
            c = AccConfig(
                account_id='1234568',
                name="test acc",
            )
            a = []
            return c == a

    def test_hash(self):
        configs = [
            AccConfig(
                account_id='1234568',
                name="test acc",
                stop_up_p=3
            ),
            AccConfig(
                account_id='1234568',
                name="test acc",
                stop_up_p=2
            ),
            AccConfig(
                account_id='1234568',
                name="test acc",
                stop_up_p=3
            ),
        ]
        unique_configs = set(configs)
        self.assertEqual(len(unique_configs), 2)

    def test_eq_method_uses_all_fields(self):
        method_code = AccConfig.__eq__.__code__
        fields = vars(AccConfig(
            account_id='1234568',
            name="test acc",
        ))
        for field in fields:
            self.assertIn(field, method_code.co_names,
                          f"Field '{field}' is not used in __eq__ method")

    def test_hash_method_uses_all_fields(self):
        method_code = AccConfig.__hash__.__code__
        fields = vars(AccConfig(
            account_id='1234568',
            name="test acc",
        ))
        for field in fields:
            self.assertIn(field, method_code.co_names,
                          f"Field '{field}' is not used in __hash__ method")

    def test_from_repr_string(self):
        """
        восстановление из repr строки работает не для всех полей
        Acc name [67862814] |u0.0 d0.0|
        Acc_name [67862814]
        """

        AccConfig.from_repr_string("Acc name [67862814] |u0.0 d0.0|")
        AccConfig.from_repr_string("Acc name [67862814] |u0.0 d0.0| ")
        AccConfig.from_repr_string("Acc name [67862814]")
        AccConfig.from_repr_string(" Acc name [67862814] ")
        AccConfig.from_repr_string("Acc_name [67862814] ")

        config_list = [
            AccConfig(account_id='672618123', name="TEST"),
            AccConfig(account_id='672618123', name="TEST TEST"),

            # разные варианты претестов
            AccConfig(account_id='672618123', name="TEST", stop_up_p=0.02, stop_down_p=2.32),

            # # полный набор - всё не стандартное. новые поля докидывать сюда
            AccConfig(
                name='TEST',
                account_id='672618883',

                stop_up_p=.2,
                stop_down_p=.34,
            ),
        ]

        for c in config_list:
            self.assertEqual(c, AccConfig.from_repr_string(str(c)), str(c))
            self.assertEqual(c, AccConfig.from_repr_string(str(c).strip()), f"'{str(c).strip()}'")


if __name__ == '__main__':
    unittest.main()
