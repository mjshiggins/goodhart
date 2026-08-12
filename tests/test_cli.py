import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


class CliTest(unittest.TestCase):
    """Runs run.py as a subprocess in a throwaway git repo."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
        shutil.copy(REPO_ROOT / 'run.py', self.tmpdir)
        self._git('init')
        self._git('config', 'user.name', 'Test')
        self._git('config', 'user.email', 'test@example.com')
        self._git('add', '.')
        self._git('commit', '-m', 'initial')

    def _git(self, *args):
        return subprocess.run(['git'] + list(args), cwd=self.tmpdir,
                              capture_output=True, text=True, check=True)

    def _run(self, *args, stdin=''):
        return subprocess.run([sys.executable, 'run.py'] + list(args),
                              input=stdin, capture_output=True, text=True,
                              cwd=self.tmpdir)

    def _commit_count(self):
        out = self._git('rev-list', '--count', 'HEAD').stdout.strip()
        return int(out)

    def _expected_total(self, lit_pixels, background, highlight):
        from datetime import datetime
        from run import visible_window
        start, _ = visible_window(datetime.now())
        background_days = (datetime.now().date() - start.date()).days + 1
        return background_days * background + lit_pixels * (highlight - background)

    def test_unsupported_character_exits_1_without_side_effects(self):
        result = self._run('hello, world')
        self.assertEqual(result.returncode, 1)
        self.assertIn("Unsupported character(s): ','", result.stdout)
        self.assertIn('Supported characters: A-Z and space.', result.stdout)
        self.assertEqual(self._commit_count(), 1)

    def test_too_wide_text_exits_1_with_fit_report(self):
        result = self._run('GOODHARTS LAW')  # needs 74 columns
        self.assertEqual(result.returncode, 1)
        self.assertIn('only 52 are available', result.stdout)
        self.assertEqual(self._commit_count(), 1)

    def test_fitting_text_reports_fit_and_previews(self):
        result = self._run('HIRE ME', stdin='n\n')
        self.assertIn('needs 38 of 52 available week-columns', result.stdout)
        self.assertIn('GitHub contribution graph preview', result.stdout)
        self.assertIn('Su ', result.stdout)  # Sunday is the first row

    def test_declining_confirmation_leaves_repo_untouched(self):
        result = self._run('HIRE ME', stdin='n\n')
        self.assertEqual(result.returncode, 0)
        self.assertIn('Aborting. Nothing was modified.', result.stdout)
        self.assertEqual(self._commit_count(), 1)

    def test_lowercase_input_is_accepted(self):
        result = self._run('hire me', stdin='n\n')
        self.assertIn('"HIRE ME" needs 38', result.stdout)

    def test_confirming_generates_commits_and_points_at_push_script(self):
        result = self._run('HI', '--highlight-commits', '3',
                           '--background-commits', '1', stdin='y\n')
        self.assertEqual(result.returncode, 0)
        self.assertIn('./push.sh', result.stdout)
        # initial commit + all generated commits ('HI' lights 32 pixels)
        self.assertEqual(self._commit_count(),
                         1 + self._expected_total(32, 1, 3))

    def test_old_history_does_not_leak_into_regenerated_repo(self):
        result = self._run('HI', '--highlight-commits', '2', stdin='y\n')
        self.assertEqual(result.returncode, 0)
        root = self._git('rev-list', '--max-parents=0', 'HEAD').stdout.strip()
        root_tree = self._git('ls-tree', '-r', '--name-only',
                              root).stdout.splitlines()
        self.assertEqual([p for p in root_tree if p.startswith('.git_old')], [])
        self.assertFalse((Path(self.tmpdir) / '.git_old').exists())

    def test_generated_commits_write_canvas_file(self):
        before = (Path(self.tmpdir) / 'run.py').read_bytes()
        result = self._run('HI', '--highlight-commits', '2', stdin='y\n')
        self.assertEqual(result.returncode, 0)
        # run.py is untouched.
        self.assertEqual((Path(self.tmpdir) / 'run.py').read_bytes(), before)
        # Each generated commit changes a real file, so no commit is empty:
        # HEAD's tree must differ from the root (initial) commit's tree.
        root = self._git('rev-list', '--max-parents=0', 'HEAD').stdout.strip()
        head_tree = self._git('rev-parse', 'HEAD^{tree}').stdout.strip()
        root_tree = self._git('rev-parse', root + '^{tree}').stdout.strip()
        self.assertNotEqual(head_tree, root_tree)
        # The generated commits write the throwaway canvas file.
        head_files = self._git('ls-tree', '-r', '--name-only',
                               'HEAD').stdout.splitlines()
        self.assertIn('canvas.txt', head_files)

    def test_readme_header_written_with_rendered_text(self):
        result = self._run('HI', '--highlight-commits', '2', stdin='y\n')
        self.assertEqual(result.returncode, 0)
        readme = (Path(self.tmpdir) / 'README.md')
        self.assertTrue(readme.exists())
        text = readme.read_text()
        self.assertIn('goodhart:start', text)
        self.assertIn('HI', text)
        # No old-style per-commit noise lines leak into the README.
        self.assertNotIn('Contribution:', text)
        # The header is part of the committed initial tree, not just worktree.
        root = self._git('rev-list', '--max-parents=0', 'HEAD').stdout.strip()
        root_files = self._git('ls-tree', '-r', '--name-only',
                               root).stdout.splitlines()
        self.assertIn('README.md', root_files)

    def test_volume_estimate_printed_before_confirmation(self):
        result = self._run('HI', stdin='n\n')
        self.assertIn('This run will generate %d commits.'
                      % self._expected_total(32, 1, 100), result.stdout)

    def test_invalid_count_flags_exit_1(self):
        for args in (['--highlight-commits', '1'],          # not > background
                     ['--background-commits', '0'],         # < 1
                     ['--highlight-commits', '2',
                      '--background-commits', '3']):        # hl <= bg
            result = self._run('HI', *args)
            self.assertEqual(result.returncode, 1, args)
            self.assertIn('highlight', result.stdout.lower())
        self.assertEqual(self._commit_count(), 1)

    def test_highlight_commits_above_day_capacity_exit_1(self):
        # +1s steps from noon: >43200 commits would spill past midnight
        result = self._run('HI', '--highlight-commits', '43201')
        self.assertEqual(result.returncode, 1)
        self.assertIn('43200', result.stdout)
        self.assertEqual(self._commit_count(), 1)

    def test_initial_commit_uses_flag_identity(self):
        result = self._run('HI', '--highlight-commits', '2',
                           '-un', 'CustomName', '-ue', 'custom@example.com',
                           stdin='y\n')
        self.assertEqual(result.returncode, 0)
        root = self._git('rev-list', '--max-parents=0', 'HEAD').stdout.strip()
        self.assertEqual(
            self._git('log', '--format=%an <%ae>', '-1', root).stdout.strip(),
            'CustomName <custom@example.com>')

    def test_preview_shows_highlight_and_background_states(self):
        result = self._run('HI', stdin='n\n')
        self.assertIn('\x1b[42m', result.stdout)    # dark green (lit pixels)
        self.assertIn('\x1b[102m', result.stdout)   # light green (background)

    def test_empty_text_exits_1_without_side_effects(self):
        result = self._run('')
        self.assertEqual(result.returncode, 1)
        self.assertIn('Text must contain at least one letter.', result.stdout)
        self.assertEqual(self._commit_count(), 1)

    def test_whitespace_only_text_exits_1_without_side_effects(self):
        result = self._run('   ')
        self.assertEqual(result.returncode, 1)
        self.assertIn('Text must contain at least one letter.', result.stdout)
        self.assertEqual(self._commit_count(), 1)


if __name__ == '__main__':
    unittest.main()
