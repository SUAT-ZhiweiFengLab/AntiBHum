"""Check the public source tree or a binary wheel before release."""
import argparse
from pathlib import Path
import zipfile
import subprocess

PUBLIC_FILES = {
    ".gitignore", ".gitattributes", "README.md", "requirements.txt", "environment.yml",
    "run_humanize_v5.py", "src/antibhum/__init__.py", "src/antibhum/__main__.py",
    "src/antibhum/cli.py", "tools/check_release.py", "tests/test_humanization.py",
    "tests/test_distribution.py", "tests/test_release_checks.py", "LICENSE", "NOTICE",
    "examples/output/.gitkeep",
    "examples/run_example.sh", "examples/README.md", "examples/HL.fasta", "examples/VHH.fasta",
}
IGNORED_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv", "venv", "build", "dist"}


def check_tree(root):
    unexpected = []
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if path.is_symlink():
            unexpected.append(rel.as_posix())
            continue
        if any(part in IGNORED_DIRS for part in rel.parts):
            continue
        if rel.parts[0] == "results" or rel.parts[:2] == ("examples", "output"):
            continue
        if path.is_file() and rel.as_posix() not in PUBLIC_FILES:
            unexpected.append(rel.as_posix())
    if (root / ".git").exists():
        tracked = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--stage", "-z"],
            check=True, capture_output=True).stdout.decode("utf-8")
        for entry in tracked.split("\0"):
            if not entry:
                continue
            info, filename = entry.split("\t", 1)
            if filename not in PUBLIC_FILES or info.split()[0] == "120000":
                unexpected.append(filename + " (Git index)")
    if unexpected:
        raise ValueError("Unexpected public files (review before publishing): " + ", ".join(unexpected))


def check_wheel(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
    if len(names) != len(set(names)):
        raise ValueError("Duplicate wheel members are not allowed")
    native = [n for n in names if n.startswith("antibhum/_core.") and n.endswith((".so", ".pyd"))]
    if len(native) != 1:
        raise ValueError("Wheel must contain exactly one native antibhum._core module")
    allowed = {"antibhum/__init__.py", "antibhum/__main__.py", "antibhum/cli.py", *native}
    for name in names:
        if name.endswith("/"):
            continue
        if name in allowed:
            continue
        parts = Path(name).parts
        if (len(parts) == 2 and parts[0].endswith(".dist-info")
                and parts[1] in {"METADATA", "WHEEL", "RECORD", "entry_points.txt", "top_level.txt"}):
            continue
        raise ValueError(f"Unexpected wheel member: {name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path)
    args = parser.parse_args()
    if args.wheel:
        check_wheel(args.wheel)
    else:
        check_tree(Path(__file__).resolve().parents[1])
    print("Release file check passed")


if __name__ == "__main__":
    main()
