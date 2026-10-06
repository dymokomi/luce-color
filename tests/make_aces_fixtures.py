#!/usr/bin/env python3
"""Write tests/fixtures/aces/reference.txt: OpenColorIO's ACES 2.0 output transforms
(builtins "ACES-OUTPUT - ACES2065-1_to_CIE-XYZ-D65 - ...") applied to a fixed grid of
ACES2065-1 colors: greys from black to far past white, saturated and near-primary colors,
random colors spread over 20 stops. Each line: transform, then AP0 r g b, then XYZ.
And tests/fixtures/aces/inverse.txt: the same transforms inverted, applied to the display
colors the forward ones made. Each line: transform, then XYZ, then AP0 r g b.

    python3 -m venv build/venv && build/venv/bin/pip install opencolorio
    build/venv/bin/python tests/make_aces_fixtures.py
"""
import random
from pathlib import Path
import PyOpenColorIO as ocio

ROOT = Path(__file__).resolve().parents[1]
TRANSFORMS = {
    "sdr100_rec709": "SDR-100nit-REC709_2.0",
    "sdr100_p3": "SDR-100nit-P3-D65_2.0",
    "hdr1000_p3": "HDR-1000nit-P3-D65_2.0",
    "hdr1000_rec2020": "HDR-1000nit-REC2020_2.0",
}
rng = random.Random(2026)
samples = [(v, v, v) for v in [0.0, 1e-4, 1e-3, 0.01, 0.05, 0.18, 0.5, 1.0, 2.0, 5.0, 10.0, 40.0, 100.0, 500.0, 4000.0]]
for v in [0.05, 0.18, 1.0, 8.0]:
    for rgb in [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0), (0, 1, 1), (1, 0, 1), (1, 0.2, 0.05), (0.05, 0.3, 1)]:
        samples.append(tuple(v * c for c in rgb))
for _ in range(400):
    level = 0.18 * 2 ** rng.uniform(-10, 10)
    samples.append(tuple(level * rng.uniform(0, 1) ** 2 for _ in range(3)))
config = ocio.Config.CreateRaw()
lines = []
inverse = []
for key, name in TRANSFORMS.items():
    builtin = ocio.BuiltinTransform("ACES-OUTPUT - ACES2065-1_to_CIE-XYZ-D65 - " + name)
    processor = config.getProcessor(builtin).getDefaultCPUProcessor()
    backward = config.getProcessor(builtin, ocio.TRANSFORM_DIR_INVERSE).getDefaultCPUProcessor()
    for rgb in samples:
        out = processor.applyRGB(list(rgb))
        lines.append(" ".join([key] + ["%.9g" % v for v in rgb] + ["%.7g" % v for v in out]))
        back = backward.applyRGB(list(out))
        inverse.append(" ".join([key] + ["%.7g" % v for v in out] + ["%.9g" % v for v in back]))
(ROOT / "tests/fixtures/aces/reference.txt").write_text("\n".join(lines) + "\n")
(ROOT / "tests/fixtures/aces/inverse.txt").write_text("\n".join(inverse) + "\n")
print(f"{len(lines)} references, {len(inverse)} inverse references (OpenColorIO {ocio.__version__})")
