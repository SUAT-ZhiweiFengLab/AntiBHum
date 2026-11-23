"""Regression tests using the real ANARCI backend and bundled sequences."""
import contextlib
import csv
import io
import tempfile
import unittest
from pathlib import Path

from abnumber import Chain
from antibhum import _core as app

ROOT = Path(__file__).resolve().parents[1]


class HumanizationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        seq = app._read_fasta_plain(ROOT / 'examples/HL.fasta')[0][1]
        self.h, _, self.l, _, _, _ = app._split_scfv(seq)

    def fasta(self, name, records):
        path = self.directory / name
        path.write_text(''.join(f'>{sid}\n{seq}\n' for sid, seq in records))
        return path

    def test_all_records_and_pair_filter(self):
        h = self.fasta('h.fa', [('one', self.h), ('two', self.h)])
        l = self.fasta('l.fa', [('one', self.l), ('two', self.l)])
        rows, stats = app._process_pair_files(h, l, 1, 1, 'all')
        self.assertEqual([r['seq_id'] for r in rows], ['one', 'two'])
        self.assertTrue(all(r['h_seq'] and r['l_seq'] for r in rows))
        rows, _ = app._process_pair_files(h, l, 1, 1, 'all', seq_id_filter='one')
        self.assertEqual([r['seq_id'] for r in rows], ['one'])
        self.assertEqual(stats['fail'], 0)

    def test_hl_csv_schema(self):
        out = self.directory / 'hl'
        app.run_humanization(scfv_fasta=ROOT / 'examples/HL.fasta', output_dir=out)
        with (out / 'humanized_results.csv').open() as handle:
            reader = csv.DictReader(handle)
            self.assertEqual(reader.fieldnames, ['date', 'template', 'seq_id',
                                                'humanized_VH_sequence', 'humanized_VL_sequence'])
            rows = list(reader)
        self.assertEqual(len(rows), 9)
        self.assertEqual(sum(bool(r['humanized_VH_sequence'] and r['humanized_VL_sequence'])
                             for r in rows), 7)
        h = self.fasta('heavy.fa', [('paired', self.h)])
        l = self.fasta('light.fa', [('paired', self.l)])
        paired_out = self.directory / 'paired'
        app.run_humanization(heavy_fasta=h, light_fasta=l, output_dir=paired_out,
                             heavy_top_n=1, light_top_n=1)
        with (paired_out / 'humanized_results.csv').open() as handle:
            paired_rows = list(csv.DictReader(handle))
        self.assertEqual(list(paired_rows[0]), list(rows[0]))
        self.assertTrue(paired_rows[0]['humanized_VH_sequence'])
        self.assertTrue(paired_rows[0]['humanized_VL_sequence'])

    def test_reverse_orientation(self):
        linker = 'GGGGSGGGGSGGGGS'
        path = self.fasta('reverse.fa', [('reverse', Chain(self.l, scheme='kabat').seq + linker + self.h)])
        rows, stats = app._process_scfv(path, 1, 1, 'all')
        self.assertEqual(stats['fail'], 0)
        self.assertEqual(rows[0]['scfv'], rows[0]['l_seq'] + linker + rows[0]['h_seq'])

    def test_single_light_is_not_heavy(self):
        path = self.fasta('light.fa', [('light', self.l)])
        rows, _ = app._process_scfv(path, 1, 1, 'all')
        self.assertEqual(rows[0]['h_seq'], '')
        self.assertEqual(rows[0]['scfv'], rows[0]['l_seq'])

    def test_cdr_and_protected_residues_unchanged(self):
        for seq, label, protection in [(self.h, 'heavy', app._heavy_protection()),
                                       (self.l, 'light', app._light_protection())]:
            original = Chain(seq, scheme='kabat')
            rows = app._humanize_chain(seq, label, 2, 'all')
            self.assertEqual(len(rows), 2)
            for row in rows:
                result = Chain(row['humanized_seq'], scheme='kabat')
                for region, residues in original.regions.items():
                    protected = protection[0].get(region, set()) | protection[1].get(region, set())
                    for pos, aa in residues.items():
                        if region.startswith('CDR') or pos.number in protected:
                            self.assertEqual(result[pos], aa, (region, pos))

    def test_hl_output_and_boundary_warning(self):
        rows, stats = app._process_scfv(ROOT / 'examples/HL.fasta', 9, 9, 'all')
        self.assertEqual(stats['fail'], 0)
        self.assertEqual(len(rows), 9)
        complete = [r for r in rows if r['scfv']]
        self.assertEqual(len(complete), 7)
        self.assertTrue(all(len(r['scfv']) == 246 for r in complete))
        self.assertTrue(stats['warnings'])  # Input terminal G is outside numbering.

    def test_vhh_single_domain_output_and_residue_preservation(self):
        seq = app._read_fasta_plain(ROOT / 'examples/VHH.fasta')[0][1]
        original = Chain(seq, scheme='kabat')
        self.assertEqual(original.chain_type, 'H')
        rows, stats = app._process_scfv(ROOT / 'examples/VHH.fasta', 9, 9, 'all')
        self.assertEqual(stats['fail'], 0)
        self.assertEqual(len(rows), 9)
        vernier, packing = app._heavy_protection()
        for row in rows:
            self.assertEqual(row['l_seq'], '')
            self.assertEqual(row['scfv'], row['h_seq'])
            result = Chain(row['h_seq'], scheme='kabat')
            for region, residues in original.regions.items():
                protected = vernier.get(region, set()) | packing.get(region, set())
                for pos, aa in residues.items():
                    if region.startswith('CDR') or pos.number in protected:
                        self.assertEqual(result[pos], aa, (region, pos))

    def test_vhh_rejects_scfv_and_light_domain(self):
        light = self.fasta('light.fa', [('light', self.l)])
        for name, path in [('scfv', ROOT / 'examples/HL.fasta'), ('light', light)]:
            with self.subTest(name=name):
                out = self.directory / name
                terminal = io.StringIO()
                with contextlib.redirect_stdout(terminal), self.assertRaises(RuntimeError):
                    app.run_humanization(vhh_fasta=path, output_dir=out,
                                         heavy_top_n=1, light_top_n=1)
                self.assertIn('exactly one heavy-chain variable domain', terminal.getvalue())
                with (out / 'humanized_results.csv').open() as handle:
                    self.assertEqual(list(csv.DictReader(handle)), [])
                self.assertEqual((out / 'humanized_scfv.fasta').read_text(), '')

    def test_reference_with_same_id_is_still_checked(self):
        ref = self.fasta('ref.fa', [('input', 'AAAA')])
        _, coverage = app._verify_against_reference([], ref, {'input': 'CCCC'})
        self.assertEqual(coverage, (0, 1))

    def test_invalid_fasta(self):
        for text in ('', 'AAAA\n', '>\nAAAA\n', '>a\n', '>a\nAA*\n', '>a\nAAAA\n>a\nCCCC\n'):
            with self.subTest(text=text):
                path = self.directory / 'bad.fa'
                path.write_text(text)
                with self.assertRaises(ValueError):
                    app._read_fasta_plain(path)

    def test_wrong_chain_rejected(self):
        with self.assertRaises(ValueError):
            app._humanize_chain(self.l, 'heavy', 1, 'all')

    def test_invalid_run_arguments(self):
        h = self.fasta('heavy.fa', [('heavy', self.h)])
        for kwargs in ({'heavy_top_n': 0}, {'seq_id_filter': 'missing'},
                       {'light_fasta': self.directory / 'missing.fa'},
                       {'verify_ref': self.directory / 'missing.fa'},
                       {'scfv_fasta': ROOT / 'examples/HL.fasta'},
                       {'vhh_fasta': ROOT / 'examples/VHH.fasta'}):
            with self.subTest(kwargs=kwargs), self.assertRaises((ValueError, OSError)):
                app.run_humanization(heavy_fasta=h, output_dir=self.directory / 'out', **kwargs)

    def test_unparseable_input_returns_failure_without_log(self):
        path = self.fasta('unknown.fa', [('unknown', 'ACDEFGHIKLMNPQRSTVWY')])
        out = self.directory / 'out'
        terminal = io.StringIO()
        with contextlib.redirect_stdout(terminal), self.assertRaises(RuntimeError):
            app.run_humanization(scfv_fasta=path, output_dir=out)
        self.assertIn('failed inputs: 1', terminal.getvalue())
        self.assertEqual({p.name for p in out.iterdir()},
                         {'humanized_results.csv', 'humanized_scfv.fasta'})


if __name__ == '__main__':
    with contextlib.redirect_stdout(io.StringIO()):
        unittest.main()
