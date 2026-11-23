# AntiBHum

AntiBHum generates antibody variable-domain humanization candidates by grafting human germline framework residues. It uses Kabat numbering, preserves Kabat CDRs and configured Vernier/packing positions, and supports scFv, VHH, and separate heavy/light inputs.

The algorithm is distributed as a Cython native extension. This public repository contains the CLI, examples, and tests; users install a platform-specific wheel. Candidate ranks describe template ordering, not affinity, immunogenicity, or clinical value.

## Installation

The current wheel is intended for **Linux x86_64 and CPython 3.10**. Other platforms require separate builds and validation. Conda supplies the ANARCI/HMMER backend; no C compiler, Cython, GPU, or CUDA installation is needed to run this workflow.

```bash
cd /path/to/AntiBHum
conda env create -f environment.yml
conda activate antibhum

# Install only the required Python packages, avoiding the unused ANARCII/Torch dependency chain.
python -m pip install --no-deps -r requirements.txt

# Replace this path with the wheel downloaded from GitHub Releases.
python -m pip install --no-deps --upgrade /path/to/antibhum-0.1.4-cp310-cp310-linux_x86_64.whl
```

If the environment already exists, activate it and run the two pip commands. `--no-deps` assumes the packages in `environment.yml` are installed. The environment file records the main dependency versions; it is not a full lockfile and installation on a fresh machine has not been validated.

Release assets belong on the [GitHub Releases page](https://github.com/SUAT-ZhiweiFengLab/AntiBHum/releases). The 0.1.4 wheel has been prepared locally but its upload is not yet confirmed. The maintainer must upload the matching wheel before users can download it and complete installation. The repository's automatically generated source archive contains only the public interface, not the native core.

Users need only the wheel, not the private source directory. This public repository does **not** support `pip install .`. Keep `--no-deps` when installing the wheel or requirements: abnumber 0.4.4 declares an ANARCII dependency that can pull in Torch and large CUDA packages, although this workflow uses the original ANARCI backend.

## Check the installation

```bash
python -c "import antibhum; from antibhum import _core; print(antibhum.__version__); print(_core.__file__)"
python -c "from abnumber import Chain; print(Chain('EVQLVETGAEVKKPGSSVKVSCKASGGTFSSYAISWVRQAPGQGLEWMGGIIPIFGTANYAQKFQGRVTITADESTSTAYMELSSLRSEDTAVYYCARGTVAGQGAFDIWGQGTMVTVSS', scheme='kabat').chain_type)"
```

The first command should print `0.1.4` and a native `.so` path inside the active environment. The second should print `H`; it actually runs the numbering backend. Importing abnumber alone does not verify ANARCI/HMMER operation.

## Run the examples

From the repository root:

```bash
# scFv input
python run_humanize_v5.py \
  --scfv examples/HL.fasta \
  --output examples/output/HL

# VHH input
python run_humanize_v5.py \
  --vhh examples/VHH.fasta \
  --output examples/output/VHH
```

Or run both with:

```bash
bash examples/run_example.sh
```

`antibhum` and `python -m antibhum` accept the same arguments as the compatibility script. `--vhh` uses the existing single-heavy-domain workflow and rejects light-chain or two-domain inputs. The tool does not identify whether an input is a VHH or apply an additional VHH-specific residue policy. The older `--scfv` single-domain input remains supported.

Each output directory contains only:

```text
humanized_results.csv
humanized_scfv.fasta
```

Warnings, failures, candidate counts, and optional reference comparisons are printed to the terminal. No report log is written. Reusing an output directory overwrites these two result files. For a manual test without overwriting earlier local results, use `--output examples/output/manual_HL` and `--output examples/output/manual_VHH`.

| Input | Record id | Input length | CSV rows | FASTA records | Output length |
|---|---|---:|---:|---:|---:|
| `HL.fasta` (scFv) | `E4_mAb` | 247 aa | 9 | 7 | 246 aa for complete scFv |
| `VHH.fasta` | `14_WT` | 122 aa | 9 | 9 | 122 aa |

HL has only seven available light-chain J templates. Ranks 8 and 9 contain only heavy-chain sequences in the CSV. The unnumbered terminal `G` is omitted, with a terminal warning. VHH CSV output contains a single `humanized_VHH_sequence` column. These inputs do not include reference FASTA files, so no reference coverage is computed. See [examples/README.md](examples/README.md).

## Options

| Option | Default | Meaning |
|---|---|---|
| `--scfv` | None | scFv FASTA; also supports a single variable domain |
| `--vhh` | None | VHH FASTA through the single-domain workflow |
| `--heavy` / `--light` | None | Separate chain FASTA files; at least one is required in this mode |
| `--output` | Required | Output directory |
| `--seq-id` | All records | Process only this FASTA id; error if absent |
| `--heavy-top` / `--light-top` | 9 / 9 | Requested template counts, positive integers |
| `--protected` | `all` | `all`, `vernier`, or `packing` |
| `--rank-mode` | `fr` | Framework-priority ranking; `full` uses the entire V region |
| `--pair-j` | `same` | Match V/J ranks; `top1` fixes J to the top result |
| `--verify-ref` | None | Reference FASTA; print sequence comparisons and coverage to the terminal |

Input modes are mutually exclusive, except that `--heavy` and `--light` can be paired. Separate chains are paired by FASTA id and rank; no linker is inferred, so the FASTA output is empty in this mode. FASTA ids are the first whitespace-delimited header token and must be unique within each file. Only the 20 standard amino acids are accepted; lowercase is converted to uppercase.

Missing files, invalid arguments, absent ids, input parsing failures, or no candidates result in a nonzero exit status. If some records fail, valid results may still be written. Insufficient templates or reference mismatches do not cause a nonzero exit status. Check terminal diagnostics. A failed template may leave a gap in candidate ranks.

CSV columns depend on the input mode:

- scFv or separate-chain input: `date`, `template`, `seq_id`, `humanized_VH_sequence`, `humanized_VL_sequence`.
- `--vhh` input: `date`, `template`, `seq_id`, `humanized_VHH_sequence`.

There is no combined scFv sequence column in CSV. Use `--vhh` to request the VHH schema; a single domain passed with `--scfv` retains the VH/VL schema. `humanized_scfv.fasta` contains complete scFv candidates or single-domain sequences, including VHH. Identical candidate sequences are not deduplicated.

## Method and limitations

- Numbering and grafting boundaries use Kabat. Only nonprotected framework positions covered by the template are replaced; CDRs, protected positions, and uncovered positions are preserved.
- Germline retrieval uses abnumber's IMGT alignment and framework-priority ranking, including similarity scoring. It is not equivalent to a Kabat-only framework identity score.
- V and J templates are paired by rank by default; this does not search all V/J combinations for a joint optimum.
- Protection uses fixed Vernier/packing positions based on the numeric Kabat position. Insertions sharing that number share the protection rule. Position-specific literature justification remains to be documented.
- Outputs retain numbered variable domains and the interdomain linker. Unnumbered terminal fragments, tags, and constant regions are omitted. Domain boundaries should be reviewed. Only one or two variable domains are supported.
- Sequence generation and residue-preservation tests do not establish affinity, stability, immunogenicity, or experimental performance. Source attribution and permission to distribute the example sequences remain to be confirmed by the maintainer.

## Tests and distribution

After installing the wheel and backend, run:

```bash
python -m unittest discover -s tests -v
python tools/check_release.py
```

Tests cover scFv orientation, single-domain output, VHH residue preservation, input validation, native loading, CLI behavior, and the absence of output logs. Generated results are excluded from Git; `.gitkeep` preserves the empty output directory.

```text
run_humanize_v5.py       Compatibility CLI entry point
src/antibhum/           Public interface and CLI
examples/               HL/VHH inputs and output directory
requirements.txt        Python packages installed with --no-deps
environment.yml         Conda backend environment
tests/                  Regression and distribution checks
tools/check_release.py  Public-tree and wheel file checks
```

Core source and build scripts live in a separate private workspace. Cython converts that source to C and then a native extension; only the extension and public interface are included in the wheel. This avoids distributing core Python source, but does not prevent binary reverse engineering. No speedup has been benchmarked. Keep the private workspace outside the public Git repository and publish only verified wheels, never source distributions or generated C files. Linux wheels are not yet certified as manylinux-compatible.

This tool uses [abnumber](https://github.com/prihoda/abnumber), [ANARCI](https://github.com/oxpig/ANARCI), and Biopython. A project license has not yet been selected; redistribution or commercial-use permission must not be assumed.

## Before publishing

Publish this directory as its own Git repository. Keep the sibling private workspace, generated results, caches, and compiler intermediates outside the public commit. Run `python tools/check_release.py` before committing; once Git is initialized, the checker also inspects tracked files, including files forced past ignore rules. The file checker does not replace a review of file contents or previous commits.

The maintainer still needs to select the project license, document the example sequences' sources and distribution permissions, and attach the verified 0.1.4 wheel to a Release. Do not infer permission to redistribute private core source from the availability of this public interface.
