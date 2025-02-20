import math
import unittest

from bot.test import TestAlgorithm


class TestTestAlg(unittest.TestCase):
    def test_no_shift(self):
        """Проверка для случая, когда step_size_shift равен 0."""
        max_change = 5.0
        step_size = 0.4
        step_size_shift = 0.0
        expected = math.ceil(max_change / step_size)  # 5.0 / 0.4 = 12.5 → ceil = 13
        result = TestAlgorithm.calc_required_step_max_cnt(max_change, step_size, step_size_shift)
        self.assertEqual(result, expected)

    def test_with_shift(self):
        """Проверка для случая с ненулевым сдвигом (step_size_shift = 0.1)."""
        max_change = 5.0
        step_size = 0.4
        step_size_shift = 0.1
        # По ручному подбору: n = 9 даёт:
        # delta = 0.4*(9 + 0.1*9*10/2) = 0.4*(9 + 4.5) = 0.4*13.5 = 5.4 >= 5.0.
        expected = 9
        result = TestAlgorithm.calc_required_step_max_cnt(max_change, step_size, step_size_shift)
        self.assertEqual(result, expected)

    def test_small_max_change(self):
        """Проверка для очень малого max_change, когда даже один шаг достаточно."""
        max_change = 0.1
        step_size = 0.4
        step_size_shift = 0.1
        # Первый шаг: 0.4*(1 + 0.1*1) = 0.44 > 0.1
        expected = 1
        result = TestAlgorithm.calc_required_step_max_cnt(max_change, step_size, step_size_shift)
        self.assertEqual(result, expected)
