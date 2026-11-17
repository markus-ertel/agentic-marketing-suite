"""Spreadsheet formula guard shared by exports (audit finding L2)."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'capabilities'))
from csv_safety import formula_like, neutralize


class CSVSafetyTests(unittest.TestCase):
    def test_formula_starts_are_detected(self):
        for value in ('=HYPERLINK("https://example.invalid","x")', '@SUM(A1)', '+cmd|\' /C calc\'!A0',
                      '-HYPERLINK("x")', '\t=1', '\r=1'):
            self.assertTrue(formula_like(value), value)
            self.assertTrue(neutralize(value).startswith("'"))

    def test_ordinary_text_and_numbers_stay_unchanged(self):
        for value in ('-20 % Rabatt', '+43 1 234', '- Punkt', 'Jetzt kaufen', '', '42', '-.5'):
            self.assertFalse(formula_like(value), value)
            self.assertEqual(neutralize(value), value)


if __name__ == '__main__':
    unittest.main()
