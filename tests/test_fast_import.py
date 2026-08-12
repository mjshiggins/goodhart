import unittest
from datetime import date, datetime

from run import fast_import_stream

FROM_SHA = 'a' * 40


class FastImportStreamTest(unittest.TestCase):
    def _stream(self, day_counts):
        return fast_import_stream(day_counts, 'Test User',
                                  'test@example.com', FROM_SHA)

    def test_one_commit_block_per_commit(self):
        stream = self._stream({date(2026, 7, 1): 2, date(2026, 6, 30): 1})
        self.assertEqual(stream.count(b'commit refs/heads/main\n'), 3)

    def test_only_first_block_has_from(self):
        stream = self._stream({date(2026, 7, 1): 2})
        self.assertEqual(stream.count(b'from ' + FROM_SHA.encode()), 1)
        first_block = stream.split(b'commit refs/heads/main\n')[1]
        self.assertIn(b'from ' + FROM_SHA.encode(), first_block)

    def test_author_and_committer_share_backdated_timestamp(self):
        stream = self._stream({date(2026, 6, 30): 1})
        epoch = int(datetime(2026, 6, 30, 12, 0, 0).timestamp())
        expected = ('Test User <test@example.com> %d' % epoch).encode()
        self.assertIn(b'author ' + expected, stream)
        self.assertIn(b'committer ' + expected, stream)

    def test_commits_within_a_day_step_by_one_second(self):
        stream = self._stream({date(2026, 6, 30): 3})
        base = int(datetime(2026, 6, 30, 12, 0, 0).timestamp())
        for i in range(3):
            self.assertIn(b'committer Test User <test@example.com> %d'
                          % (base + i), stream)

    def test_chronological_order_oldest_first(self):
        stream = self._stream({date(2026, 7, 1): 1, date(2026, 6, 30): 1})
        self.assertLess(stream.index(b'Contribution: 2026-06-30'),
                        stream.index(b'Contribution: 2026-07-01'))

    def test_data_length_matches_message_bytes(self):
        stream = self._stream({date(2026, 6, 30): 1})
        msg = b'Contribution: 2026-06-30 12:00:00'
        self.assertIn(b'data %d\n' % len(msg) + msg, stream)

    def test_each_commit_modifies_canvas_file(self):
        # Every commit must touch a throwaway file so no commit is empty
        # (empty commits are unreliably counted by GitHub).
        stream = self._stream({date(2026, 6, 30): 2})
        self.assertEqual(stream.count(b'M 644 inline canvas.txt\n'), 2)

    def test_canvas_content_differs_per_commit(self):
        # Distinct content per commit guarantees each tree is unique.
        stream = self._stream({date(2026, 6, 30): 2})
        blocks = stream.split(b'M 644 inline canvas.txt\n')[1:]
        payloads = [b.split(b'\n', 2)[1] for b in blocks]  # the line after data
        self.assertEqual(len(payloads), 2)
        self.assertNotEqual(payloads[0], payloads[1])

    def test_filemodify_comes_after_from(self):
        stream = self._stream({date(2026, 6, 30): 1})
        self.assertLess(stream.index(b'from ' + FROM_SHA.encode()),
                        stream.index(b'M 644 inline canvas.txt'))


if __name__ == '__main__':
    unittest.main()
