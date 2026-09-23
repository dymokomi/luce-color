#!/usr/bin/env python3
"""Run the color module's own test blocks in native and C comparison modes."""
import argparse
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--base", type=Path, default=ROOT.parent / ("luce-base/build/luce-base.exe" if os.name == "nt" else "luce-base/build/luce-base"))
args = parser.parse_args()
env = dict(os.environ, LUCE_BASE=str(args.base.resolve()))
for name in ["color", "transfer", "xyz", "lab", "cam16", "hsl", "space", "oklab"]:
    module = ROOT / f"src/luce_color/{name}.lucb"
    for flags in [["--native"], ["--backend=c"]]:
        subprocess.run([str(args.base.resolve()), "test", str(module), *flags], check=True, env=env, timeout=300)
print("PASS luce-color colour science: Oklab, transfer curves, XYZ, Lab, CAM16, HSL and spaces, native and comparison modes")
