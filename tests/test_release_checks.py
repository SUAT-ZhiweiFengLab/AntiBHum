"""Ensure release checks catch accidental source publication."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('release_check', ROOT / 'tools/check_release.py')
release_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_check)


class ReleaseChecksTests(unittest.TestCase):
    def test_symlink_in_ignored_output_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / 'examples/output'
            output.mkdir(parents=True)
            (output / 'private.pyx').symlink_to(root / 'missing-private.pyx')
            with self.assertRaisesRegex(ValueError, 'private.pyx'):
                release_check.check_tree(root)

    @unittest.skipUnless(shutil.which('git'), 'Git is required for index checks')
    def test_force_tracked_core_in_ignored_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / '.gitignore').write_text('results/\n')
            (root / 'results').mkdir()
            (root / 'results/core.pyx').write_text('# private source\n')
            subprocess.run(['git', '-C', tmp, 'init', '-q'], check=True)
            subprocess.run(['git', '-C', tmp, 'add', '-f', 'results/core.pyx'], check=True)
            with self.assertRaisesRegex(ValueError, 'Git index'):
                release_check.check_tree(root)

    def test_wheel_with_core_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            wheel = Path(tmp) / 'example.whl'
            with zipfile.ZipFile(wheel, 'w') as archive:
                archive.writestr('antibhum/_core.example.so', b'example binary')
                archive.writestr('antibhum/_core.pyx', '# private source\n')
            with self.assertRaisesRegex(ValueError, '_core.pyx'):
                release_check.check_wheel(wheel)
