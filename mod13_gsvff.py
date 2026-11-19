
import unittest
import re
from datetime import datetime


# Input validation functions

def valid_symbol(symbol):
    return bool(re.fullmatch(r"[A-Z]{1,7}", symbol))


def valid_chart_type(chart_type):
    return chart_type in ("1", "2")


def valid_time_series(time_series):
    return time_series in ("1", "2", "3", "4")


def valid_date(date):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        return False

    try:
        datetime.strptime(date, "%Y-%m-%d")
        return True
    except ValueError:
        return False


# Unit tests

class TestStockInputs(unittest.TestCase):

    def test_symbol(self):
        self.assertTrue(valid_symbol("AAPL"))
        self.assertTrue(valid_symbol("IBM"))
        self.assertFalse(valid_symbol("aapl"))
        self.assertFalse(valid_symbol("ABCDEFGH"))
        self.assertFalse(valid_symbol("AAPL1"))
        self.assertFalse(valid_symbol(""))

    def test_chart_type(self):
        self.assertTrue(valid_chart_type("1"))
        self.assertTrue(valid_chart_type("2"))
        self.assertFalse(valid_chart_type("3"))
        self.assertFalse(valid_chart_type("0"))
        self.assertFalse(valid_chart_type("A"))

    def test_time_series(self):
        self.assertTrue(valid_time_series("1"))
        self.assertTrue(valid_time_series("2"))
        self.assertTrue(valid_time_series("3"))
        self.assertTrue(valid_time_series("4"))
        self.assertFalse(valid_time_series("5"))
        self.assertFalse(valid_time_series("A"))

    def test_start_date(self):
        self.assertTrue(valid_date("2026-01-15"))
        self.assertFalse(valid_date("01-15-2026"))
        self.assertFalse(valid_date("2026-13-01"))
        self.assertFalse(valid_date("2026-02-30"))
        self.assertFalse(valid_date("invalid"))

    def test_end_date(self):
        self.assertTrue(valid_date("2026-11-19"))
        self.assertFalse(valid_date("11/19/2026"))
        self.assertFalse(valid_date("2026-00-10"))
        self.assertFalse(valid_date("2026-02-30"))
        self.assertFalse(valid_date(""))


if __name__ == "__main__":
    unittest.main()
