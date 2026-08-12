import unittest
from datetime import date, datetime

from run import build_day_counts, layout_text, letters


class BuildDayCountsTest(unittest.TestCase):
    # Fixed frame: window starts Sunday 2025-07-13, today is Tue 2026-07-14.
    START = datetime(2025, 7, 13)
    TODAY = datetime(2026, 7, 14)

    def _counts(self, text='HI', offset=0, background=1, highlight=100):
        columns = layout_text(text, letters) if text else []
        return build_day_counts(columns, self.START, self.TODAY, offset,
                                background, highlight)

    def test_every_visible_day_has_a_count(self):
        counts = self._counts(text='')
        self.assertEqual(len(counts), 367)  # 52*7 + Sun..Tue of current week
        self.assertEqual(min(counts), date(2025, 7, 13))
        self.assertEqual(max(counts), date(2026, 7, 14))

    def test_background_days_get_background_count(self):
        counts = self._counts(text='')
        self.assertTrue(all(v == 1 for v in counts.values()))

    def test_lit_pixels_get_highlight_count_not_sum(self):
        counts = self._counts(text='HI', offset=0, highlight=100)
        # 'H' column 0 is all seven rows' first char '#': days Sun..Sat of week 0
        self.assertEqual(counts[date(2025, 7, 13)], 100)
        # 'H' column 1 rows 0-2 and 4-6 are blank; row 3 is '#'
        self.assertEqual(counts[date(2025, 7, 20)], 1)     # week 1, Sunday
        self.assertEqual(counts[date(2025, 7, 23)], 100)   # week 1, Wednesday

    def test_offset_shifts_lit_days(self):
        counts = self._counts(text='HI', offset=3, highlight=100)
        self.assertEqual(counts[date(2025, 7, 13)], 1)       # week 0 now background
        self.assertEqual(counts[date(2025, 8, 3)], 100)      # week 3, Sunday

    def test_total_commit_volume(self):
        counts = self._counts(text='HI', offset=0, background=1, highlight=3)
        # 367 background days; 'HI' lights 32 pixels, each 3 instead of 1.
        self.assertEqual(sum(counts.values()), 367 + 32 * 2)


if __name__ == '__main__':
    unittest.main()
