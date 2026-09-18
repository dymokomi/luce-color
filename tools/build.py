#!/usr/bin/env python3
"""Compile a Base consumer through the package's real manifest and exports."""
import argparse
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def build(entry, output, base, opt=0, backend="native"):
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    flags = ["--native", "--opt", str(opt)] if backend == "native" else ["--backend=c"]
    subprocess.run([str(base.resolve()), "build", str(entry.resolve()), *flags,
                    "-o", str(output)], check=True, cwd=ROOT)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("entry", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--base", type=Path, default=Path(os.environ.get(
        "LUCE_BASE_COMPILER", ROOT.parent / ("luce-base/build/luce-base.exe" if os.name == "nt" else "luce-base/build/luce-base"))))
    parser.add_argument("--opt", type=int, choices=range(4), default=0)
    parser.add_argument("--backend", choices=["native", "c"], default="native")
    args = parser.parse_args()
    build(args.entry, args.output, args.base, args.opt, args.backend)
