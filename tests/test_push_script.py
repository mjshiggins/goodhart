import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


class PushScriptTest(unittest.TestCase):
    """Runs push.sh in a throwaway repo whose origin is a local bare repo."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
        self.work = self.tmpdir / 'work'
        self.origin = self.tmpdir / 'origin.git'
        self.work.mkdir()
        subprocess.run(['git', 'init', '--bare', str(self.origin)],
                       capture_output=True, check=True)
        shutil.copy(REPO_ROOT / 'push.sh', self.work)
        for args in (['init'],
                     ['config', 'user.name', 'Test'],
                     ['config', 'user.email', 'test@example.com'],
                     ['add', '.'],
                     ['commit', '-m', 'initial'],
                     ['remote', 'add', 'origin', str(self.origin)]):
            subprocess.run(['git'] + args, cwd=self.work,
                           capture_output=True, check=True)

    def _run_push(self, stdin):
        return subprocess.run(['bash', 'push.sh'], input=stdin,
                              capture_output=True, text=True, cwd=self.work)

    def test_declining_aborts_without_pushing(self):
        result = self._run_push('n\n')
        self.assertEqual(result.returncode, 1)
        self.assertIn('Aborted.', result.stdout)
        refs = subprocess.run(['git', 'branch'], cwd=self.origin,
                              capture_output=True, text=True)
        self.assertEqual(refs.stdout.strip(), '')  # nothing pushed

    def test_prompt_shows_remote_url_and_warns_force(self):
        result = self._run_push('n\n')
        self.assertIn(str(self.origin), result.stdout)
        self.assertIn('FORCE PUSH', result.stdout)

    def test_confirming_force_pushes_main_to_origin(self):
        result = self._run_push('y\n')
        self.assertEqual(result.returncode, 0)
        refs = subprocess.run(['git', 'branch'], cwd=self.origin,
                              capture_output=True, text=True)
        self.assertIn('main', refs.stdout)


if __name__ == '__main__':
    unittest.main()
