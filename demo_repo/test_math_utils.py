import unittest
from math_utils import add, calculate_discount


class TestMathUtils(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)

    def test_calculate_discount(self):
        # Original price $100 with 20% discount should be $80
        self.assertEqual(calculate_discount(100.0, 20.0), 80.0)

    def test_calculate_discount_zero(self):
        self.assertEqual(calculate_discount(50.0, 0.0), 50.0)


if __name__ == "__main__":
    unittest.main()
