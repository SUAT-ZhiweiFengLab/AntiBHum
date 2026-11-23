"""Integration checks for the installed binary distribution and CLI."""
import importlib.machinery
from pathlib import Path
import subprocess
import sys
import csv
import tempfile
import unittest

from antibhum import _core

ROOT = Path(__file__).resolve().parents[1]


class DistributionTests(unittest.TestCase):
    def test_core_is_native_extension(self):
        self.assertTrue(any(_core.__file__.endswith(suffix)
                            for suffix in importlib.machinery.EXTENSION_SUFFIXES), _core.__file__)

    def test_module_and_legacy_help(self):
        for args in (["-m", "antibhum"], [str(ROOT / "run_humanize_v5.py")]):
            with self.subTest(args=args):
                result = subprocess.run([sys.executable, *args, "--help"], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("--verify-ref", result.stdout)
                self.assertIn("--vhh", result.stdout)
                self.assertFalse(any("\u4e00" <= c <= "\u9fff" for c in result.stdout + result.stderr))

    def test_cli_invalid_inputs_return_nonzero(self):
        for extra in ([], ["--heavy", "missing.fa"], ["--heavy-top", "0"]):
            with self.subTest(extra=extra):
                result = subprocess.run([sys.executable, "-m", "antibhum", "--output", "unused", *extra],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn("Error:", result.stderr)

    def test_vhh_alias_output_and_input_conflicts(self):
        source = str(ROOT / "examples/VHH.fasta")
        with tempfile.TemporaryDirectory() as tmp:
            outputs = []
            for option in ("--vhh", "--scfv"):
                out = Path(tmp) / option[2:]
                result = subprocess.run(
                    [sys.executable, "-m", "antibhum", option, source, "--output", str(out)],
                    capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                with (out / "humanized_results.csv").open() as handle:
                    rows = list(csv.DictReader(handle))
                self.assertEqual(len(rows), 9)
                sequence_column = ('humanized_VHH_sequence' if option == '--vhh'
                                   else 'humanized_VH_sequence')
                expected_columns = ['date', 'template', 'seq_id'] + (
                    ['humanized_VHH_sequence'] if option == '--vhh' else
                    ['humanized_VH_sequence', 'humanized_VL_sequence'])
                self.assertEqual(list(rows[0]), expected_columns)
                self.assertTrue(all(r[sequence_column] for r in rows))
                if option == '--scfv':
                    self.assertTrue(all(not r['humanized_VL_sequence'] for r in rows))
                self.assertEqual({p.name for p in out.iterdir()},
                                 {'humanized_results.csv', 'humanized_scfv.fasta'})
                self.assertFalse(any('\u4e00' <= c <= '\u9fff' for c in result.stdout + result.stderr))
                outputs.append((rows, (out / "humanized_scfv.fasta").read_text()))
            self.assertEqual(outputs[0][1], outputs[1][1])
            for vhh, single in zip(outputs[0][0], outputs[1][0]):
                self.assertEqual(vhh['humanized_VHH_sequence'], single['humanized_VH_sequence'])
                for key in ('date', 'template', 'seq_id'):
                    self.assertEqual(vhh[key], single[key])
            reference = Path(tmp) / "reference.fa"
            reference.write_text(">candidate\n" + outputs[0][0][0]['humanized_VHH_sequence'] + "\n")
            verified = Path(tmp) / "verified"
            result = subprocess.run(
                [sys.executable, "-m", "antibhum", "--vhh", source,
                 "--verify-ref", str(reference), "--output", str(verified)],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Reference coverage: 1/1", result.stdout)
            self.assertEqual({p.name for p in verified.iterdir()},
                             {'humanized_results.csv', 'humanized_scfv.fasta'})
            for option in ("--scfv", "--heavy", "--light"):
                result = subprocess.run(
                    [sys.executable, "-m", "antibhum", "--vhh", source,
                     option, source, "--output", str(Path(tmp) / "conflict")],
                    capture_output=True, text=True)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertFalse((Path(tmp) / "conflict").exists())
