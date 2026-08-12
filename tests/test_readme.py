import unittest

from run import (layout_text, letters, render_text_art, readme_with_header,
                 HEADER_START, HEADER_END)


class RenderTextArtTest(unittest.TestCase):
    def test_has_seven_rows(self):
        art = render_text_art(layout_text('HI', letters))
        self.assertEqual(len(art.split('\n')), 7)

    def test_lit_pixels_become_blocks_blanks_are_spaces(self):
        # 'I' top row is '#####' -> five block chars on the first line.
        art = render_text_art(layout_text('I', letters))
        first_row = art.split('\n')[0]
        self.assertEqual(first_row.count('\u2588'), 5)

    def test_all_blank_column_renders_empty_row(self):
        # A single space glyph has no lit pixels; every row is blank.
        art = render_text_art(layout_text(' ', letters))
        self.assertEqual(art.replace('\n', '').strip(), '')


class ReadmeWithHeaderTest(unittest.TestCase):
    def test_inserts_block_at_top_when_absent(self):
        out = readme_with_header('# goodhart\n\nbody', 'HI', 'ART')
        self.assertTrue(out.startswith(HEADER_START))
        self.assertIn('# goodhart', out)
        self.assertIn('HI', out)
        self.assertIn('ART', out)

    def test_replacing_is_idempotent(self):
        once = readme_with_header('# goodhart\n', 'HI', 'ARTONE')
        twice = readme_with_header(once, 'BYE', 'ARTTWO')
        # Only one header block ever exists.
        self.assertEqual(twice.count(HEADER_START), 1)
        self.assertEqual(twice.count(HEADER_END), 1)
        # Latest content wins; stale content is gone.
        self.assertIn('BYE', twice)
        self.assertIn('ARTTWO', twice)
        self.assertNotIn('ARTONE', twice)
        # Original body is preserved.
        self.assertIn('# goodhart', twice)

    def test_preserves_content_after_the_block_on_replace(self):
        base = readme_with_header('# goodhart\n\noriginal body\n', 'HI', 'ART')
        replaced = readme_with_header(base, 'HI', 'ART2')
        self.assertIn('original body', replaced)

    def test_inline_marker_mentions_are_not_treated_as_a_block(self):
        # README prose that merely *mentions* the markers inline (e.g. the
        # tool's own docs) must NOT be mistaken for an existing header block.
        doc = ('# goodhart\n\n'
               'It writes between `%s` / `%s` markers.\n' %
               (HEADER_START, HEADER_END))
        out = readme_with_header(doc, 'HI', 'ART')
        # Header is prepended at the very top, not spliced into the sentence.
        self.assertTrue(out.startswith(HEADER_START + '\n'))
        # The documentation sentence is preserved intact.
        self.assertIn('It writes between', out)
        self.assertIn('markers.', out)

    def test_idempotent_even_when_prose_mentions_markers_inline(self):
        doc = '# goodhart\n\nMentions `%s` inline.\n' % HEADER_START
        once = readme_with_header(doc, 'HI', 'A1')
        twice = readme_with_header(once, 'BYE', 'A2')
        # Exactly one real (standalone-line) start marker after replacement.
        standalone = sum(1 for ln in twice.split('\n')
                         if ln.strip() == HEADER_START)
        self.assertEqual(standalone, 1)
        self.assertIn('BYE', twice)
        self.assertNotIn('A1', twice)
        self.assertIn('Mentions', twice)


if __name__ == '__main__':
    unittest.main()
