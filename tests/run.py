#!/usr/bin/env python3
"""luce-color's gate, in native and C comparison modes:

- every module's own test blocks (the icc module's with its tests/icc fragments);
- the ACES 2.0 output transforms (src/aces) against OpenColorIO's (tests/fixtures/aces);
- the icc oracle driver (tests/icc_tool.lucb) on every profile of tests/fixtures/icc gives
  skcms's dump (expected.txt) and Skia's color spaces (spaces.txt) byte for byte, and its
  pixel-format sweeps hash as skcms's (formats.sha256).
"""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/icc"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--base", type=Path, default=ROOT.parent / ("luce-base/build/luce-base.exe" if os.name == "nt" else "luce-base/build/luce-base"))
args = parser.parse_args()
base = args.base.resolve()
env = dict(os.environ, LUCE_BASE=str(base))
MODES = [["--native"], ["--backend=c"]]


def run(command, **options):
    return subprocess.run([str(part) for part in command], check=True, env=env, cwd=ROOT, timeout=600, **options)


for name in ["color", "transfer", "xyz", "lab", "cam16", "hsl", "space", "oklab"]:
    for flags in MODES:
        run([base, "test", ROOT / f"src/{name}.lucb", *flags])
for flags in MODES:
    run([base, "test", ROOT / "src/icc", *flags])
    run([base, "test", ROOT / "src/aces", *flags])

profiles = sorted(p.name for p in FIXTURES.glob("*.icc"))
expected = (FIXTURES / "expected.txt").read_bytes()
spaces = (FIXTURES / "spaces.txt").read_bytes()
hashes = dict(reversed(line.split("  ")) for line in (FIXTURES / "formats.sha256").read_text().splitlines() if line)
with tempfile.TemporaryDirectory() as tmp:
    for flags in MODES:
        tool = Path(tmp) / f"icc_tool{flags[0].replace('-', '_').replace('=', '_')}"
        run([base, "build", ROOT / "tests/icc_tool.lucb", *flags, "-o", tool])
        dump = subprocess.run([tool, *profiles], check=True, cwd=FIXTURES, capture_output=True, timeout=300).stdout
        if dump != expected:
            raise SystemExit(f"FAIL icc_tool {flags[0]}: the dump differs from skcms's (tests/fixtures/icc/expected.txt)")
        found = subprocess.run([tool, "--spaces", *profiles], check=True, cwd=FIXTURES, capture_output=True, timeout=300).stdout
        if found != spaces:
            raise SystemExit(f"FAIL icc_tool {flags[0]}: the color spaces differ from Skia's (tests/fixtures/icc/spaces.txt)")
        for profile, digest in hashes.items():
            sweep = subprocess.run([tool, "--formats", profile], check=True, cwd=FIXTURES, capture_output=True, timeout=300).stdout
            if hashlib.sha256(sweep).hexdigest() != digest:
                raise SystemExit(f"FAIL icc_tool {flags[0]} --formats {profile}: the pixels differ from skcms's")
# ACES 2.0 and its inverse against OpenColorIO's builtin output transforms (tests/make_aces_fixtures.py).
with tempfile.TemporaryDirectory() as tmp:
    for flags in MODES:
        tool = Path(tmp) / f"aces_check{flags[0].replace('-', '_').replace('=', '_')}"
        run([base, "build", ROOT / "tests/aces_check.lucb", *flags, "-o", tool])
        run([tool, ROOT / "tests/fixtures/aces/reference.txt", ROOT / "tests/fixtures/aces/inverse.txt"])
print("PASS luce-color color science: Oklab, transfer curves, XYZ, Lab, CAM16, HSL, spaces, ACES 2.0 (OpenColorIO's within 1e-4) and its inverse and ICC (skcms's dumps and Skia's color spaces to the bit), native and comparison modes")
