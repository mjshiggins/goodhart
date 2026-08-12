import unittest
from datetime import datetime

from run import fit_report, layout_text, letters, visible_window


class VisibleWindowTest(unittest.TestCase):
    def test_starts_on_sunday_52_weeks_before_current_week(self):
        # Tue 2026-07-14 -> current week's Sunday is 2026-07-12,
        # window starts 52 weeks earlier on Sunday 2025-07-13.
        start, available = visible_window(datetime(2026, 7, 14))
        self.assertEqual(start.strftime('%Y-%m-%d %a'), '2025-07-13 Sun')
        self.assertEqual(available, 52)

    def test_when_today_is_sunday(self):
        # Sun 2026-07-12 is its own week's Sunday.
        start, available = visible_window(datetime(2026, 7, 12))
        self.assertEqual(start.strftime('%Y-%m-%d %a'), '2025-07-13 Sun')
        self.assertEqual(available, 52)

    def test_start_is_midnight_regardless_of_time_of_day(self):
        start, _ = visible_window(datetime(2026, 7, 14, 23, 59, 58))
        self.assertEqual(start, datetime(2025, 7, 13, 0, 0, 0))


class LayoutTextTest(unittest.TestCase):
    def test_single_letter_is_five_columns(self):
        self.assertEqual(len(layout_text('A', letters)), 5)

    def test_spacer_column_between_glyphs(self):
        cols = layout_text('HI', letters)
        self.assertEqual(len(cols), 11)  # 5 + 1 spacer + 5
        self.assertEqual(cols[5], [False] * 7)

    def test_columns_are_seven_rows(self):
        for col in layout_text('HI', letters):
            self.assertEqual(len(col), 7)

    def test_space_glyph_is_two_columns(self):
        # 'A B' = 5 + 1 + 2 + 1 + 5
        self.assertEqual(len(layout_text('A B', letters)), 14)

    def test_hire_me_needs_38_columns(self):
        self.assertEqual(len(layout_text('HIRE ME', letters)), 38)


class FitReportTest(unittest.TestCase):
    def test_fitting_text_reports_margins(self):
        msg, fits = fit_report('HIRE ME', 38, 52)
        self.assertTrue(fits)
        self.assertIn('needs 38 of 52', msg)
        self.assertIn('14 columns of margin', msg)
        self.assertIn('7 left, 7 right', msg)

    def test_too_wide_text_reports_overflow_and_cut_estimate(self):
        msg, fits = fit_report('GOODHARTSLAW', 71, 52)
        self.assertFalse(fits)
        self.assertIn('19 over', msg)
        self.assertIn('4 character(s)', msg)


if __name__ == '__main__':
    unittest.main()
