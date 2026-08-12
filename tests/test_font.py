import string
import unittest

from run import letters


class FontTest(unittest.TestCase):
    def test_covers_a_to_z_and_space(self):
        self.assertEqual(set(letters), set(string.ascii_uppercase) | {' '})

    def test_every_glyph_has_seven_rows(self):
        for ch, glyph in letters.items():
            self.assertEqual(len(glyph), 7, 'glyph %r must have 7 rows' % ch)

    def test_letters_are_five_columns_wide_space_is_two(self):
        for ch, glyph in letters.items():
            expected_width = 2 if ch == ' ' else 5
            for row in glyph:
                self.assertEqual(len(row), expected_width,
                                 'glyph %r row %r has wrong width' % (ch, row))

    def test_glyphs_use_only_hash_and_blank(self):
        for ch, glyph in letters.items():
            for row in glyph:
                self.assertTrue(set(row) <= {'#', ' '},
                                'glyph %r row %r has stray chars' % (ch, row))


if __name__ == '__main__':
    unittest.main()
