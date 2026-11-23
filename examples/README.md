# Examples

| File | Record id | Input |
|---|---|---|
| `HL.fasta` | `E4_mAb` | VH-linker-VL scFv, 247 amino acids |
| `VHH.fasta` | `14_WT` | Nanobody starting sequence, 122 amino acids |

Install the binary wheel and ANARCI/HMMER environment as described in the project README, then run from the repository root:

```bash
bash examples/run_example.sh
```

To run each case separately:

```bash
python run_humanize_v5.py --scfv examples/HL.fasta --output examples/output/HL
python run_humanize_v5.py --vhh examples/VHH.fasta --output examples/output/VHH
```

The script uses the active environment's `python`. Override it with `PYTHON=/path/to/python bash examples/run_example.sh` if needed.

```text
output/
├── HL/
│   ├── humanized_results.csv
│   └── humanized_scfv.fasta
└── VHH/
    ├── humanized_results.csv
    └── humanized_scfv.fasta
```

No report log is generated. Diagnostics and candidate counts appear in the terminal. Repeated runs overwrite the two result files. Use a different output directory to retain earlier results. Generated files remain local and are excluded from Git.

Expected results with the current defaults:

- HL: 9 CSV rows and 7 complete scFv FASTA records, each 246 amino acids. Ranks 8 and 9 have only a heavy chain because only seven light-chain J templates are available. The unnumbered terminal G is omitted with a warning.
- VHH: 9 CSV rows and 9 single-domain FASTA records, each 122 amino acids. There is no light-chain column in VHH mode. The legacy filename `humanized_scfv.fasta` also applies to single-domain output.

`--vhh` requires one heavy-chain variable domain and rejects light-chain or scFv inputs; it does not add a VHH-specific algorithm or automatically identify VHH sequences. The older `--scfv` single-domain input is still supported. Both cases preserve configured protected residues and Kabat CDRs.

HL CSV columns are `date`, `template`, `seq_id`, `humanized_VH_sequence`, and `humanized_VL_sequence`. VHH CSV columns are `date`, `template`, `seq_id`, and `humanized_VHH_sequence`. Combined scFv sequences are available in FASTA, not in a CSV column. Input mode determines the CSV schema; use `--vhh` for the VHH column name.

There are no reference FASTA files for these examples. Output sequences are generated candidates, not independent validation references. Input provenance and redistribution permission remain to be confirmed by the maintainer.
