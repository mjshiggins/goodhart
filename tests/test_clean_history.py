import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


class CleanHistoryBranchTest(unittest.TestCase):
    """clean_git_history must initialize directly on `main` with no
    transient `master` branch left behind."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
        prev = os.getcwd()
        self.addCleanup(os.chdir, prev)
        (self.tmpdir / 'file.txt').write_text('hi')
        os.chdir(self.tmpdir)
        sys.path.insert(0, str(REPO_ROOT))

    def _current_branch(self):
        return subprocess.check_output(
            ['git', 'symbolic-ref', '--short', 'HEAD']).decode().strip()

    def test_initial_commit_is_on_main_branch(self):
        import run
        run.clean_git_history('Test', 'test@example.com')
        self.assertEqual(self._current_branch(), 'main')

    def test_no_master_branch_exists(self):
        import run
        run.clean_git_history('Test', 'test@example.com')
        branches = subprocess.check_output(
            ['git', 'branch', '--format=%(refname:short)']).decode().split()
        self.assertNotIn('master', branches)
        self.assertEqual(branches, ['main'])


if __name__ == '__main__':
    unittest.main()
