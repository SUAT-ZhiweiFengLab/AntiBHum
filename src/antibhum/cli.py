"""Public command-line interface. The algorithm lives in a compiled extension."""

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Antibody framework humanization v5 (FR-ranked templates, V_i/J_i pairing, scFv splitting)"
    )
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument("--scfv", default=None,
                        help="scFv FASTA; cannot be combined with --vhh or --heavy/--light")
    inputs.add_argument("--vhh", default=None,
                        help="VHH FASTA (one heavy-chain variable domain); cannot be combined with other input modes")
    parser.add_argument("--seq-id", dest="seq_id", default=None,
                        help="Process only this FASTA record id")
    parser.add_argument("--heavy", default=None, help="Heavy-chain FASTA path")
    parser.add_argument("--light", default=None, help="Light-chain FASTA path")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--heavy-top", type=int, default=9,
                        help="Number of heavy-chain V/J templates")
    parser.add_argument("--light-top", type=int, default=9,
                        help="Number of light-chain V/J templates")
    parser.add_argument("--protected", default="all",
                        choices=["all", "vernier", "packing"], help="Protected residue configuration")
    parser.add_argument("--rank-mode", default="fr", choices=["fr", "full"],
                        help="Template ranking: fr=framework priority (default), full=entire V region")
    parser.add_argument("--pair-j", default="same", choices=["same", "top1"],
                        help="J pairing: same=match V/J ranks (default), top1=use the top J throughout")
    parser.add_argument("--verify-ref", default=None,
                        help="Reference FASTA; print exact sequence comparisons to the terminal")
    args = parser.parse_args()
    if args.vhh and (args.heavy or args.light):
        parser.error("--vhh cannot be combined with --heavy/--light")

    try:
        from ._core import run_humanization
    except ImportError as exc:
        parser.exit(1, f"Cannot load the AntiBHum native core; install a wheel matching your Python and platform. Details: {exc}\n")

    try:
        run_humanization(
            heavy_fasta=args.heavy,
            light_fasta=args.light,
            scfv_fasta=args.scfv,
            vhh_fasta=args.vhh,
            output_dir=args.output,
            heavy_top_n=args.heavy_top,
            light_top_n=args.light_top,
            protected_type=args.protected,
            seq_id_filter=args.seq_id,
            rank_mode=args.rank_mode,
            pair_j=args.pair_j,
            verify_ref=args.verify_ref,
        )
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(1, f"Error: {exc}\n")
