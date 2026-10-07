#!/usr/bin/env python3
"""Write the synthetic ICC profiles of tests/fixtures/icc: every tag layout skcms reads, built
by a plain Python writer so they carry no third-party data.

- para-types.icc: RGB with para function types 0, 3 and 4, a chad and a cicp tag
- para-types-12.icc: para function types 1 and 2
- curv-gamma.icc: RGB with one-entry (gamma) and empty (identity) curv tags and a cicp tag,
  ICC v2
- gray-ktrc.icc: gray with a 1024-entry kTRC
- mft2-lab.icc: RGB to Lab through a 16-bit mft2 A2B0 (9 grid points) and B2A0
- mft1-cmyk.icc: CMYK to Lab through an 8-bit mft1 A2B0 (3 grid points a channel) and B2A0
- mab-xyz.icc: RGB to XYZ through an mAB A2B0 (A curves, 8-bit CLUT, M curves, matrix, B
  curves) and an mBA B2A0 (B curves, matrix, M curves, 16-bit CLUT, A curves)
- identity-tables.icc: RGB with identity tables, which skcms rewrites as the identity
- bad-*.icc: profiles skcms refuses (signature, illuminant, tag past the end, version 5,
  a para curve with a = 0 or one whose d = -b/a is negative, a CLUT with one grid point)

The expected dumps (expected.txt) come from the skcms oracle, see tests/icc_oracle.
"""
import math
import struct
from pathlib import Path

OUT = Path(__file__).resolve().parent / "fixtures" / "icc"


def s15(v):
    return struct.pack(">i", int(round(v * 65536)))


def xyz_tag(x, y, z):
    return b"XYZ \0\0\0\0" + s15(x) + s15(y) + s15(z)


def curv(values):
    return b"curv\0\0\0\0" + struct.pack(">I", len(values)) + b"".join(struct.pack(">H", v) for v in values)


def curv_gamma(g):
    return b"curv\0\0\0\0" + struct.pack(">IH", 1, int(round(g * 256))) + b"\0\0"


def para(kind, params):
    return b"para\0\0\0\0" + struct.pack(">HH", kind, 0) + b"".join(s15(p) for p in params)


def pad4(data):
    return data + b"\0" * (-len(data) % 4)


def profile(dcs, pcs, tags, version=0x04300000, illuminant=(0.9642, 1.0, 0.8249), signature=b"acsp", cls=b"mntr"):
    """tags: list of (signature, data); identical data is written once and shared."""
    count = len(tags)
    offset = 128 + 4 + 12 * count
    table = b""
    body = b""
    placed = {}
    for sig, data in tags:
        if data in placed:
            at = placed[data]
        else:
            at = offset + len(body)
            placed[data] = at
            body += pad4(data)
        table += sig + struct.pack(">II", at, len(data))
    size = offset + len(body)
    header = struct.pack(">I", size) + b"lucc" + struct.pack(">I", version) + cls + dcs + pcs
    header += b"\0" * 12 + signature + b"APPL" + b"\0" * 4 + b"\0" * 8 + b"\0" * 8 + struct.pack(">I", 0)
    header += s15(illuminant[0]) + s15(illuminant[1]) + s15(illuminant[2]) + b"lucc" + b"\0" * 16 + b"\0" * 28
    assert len(header) == 128
    return header + struct.pack(">I", count) + table + body


# The colorimetry the LUT profiles encode: sRGB's.
SRGB_TO_XYZ = [[0.436065674, 0.385147095, 0.143066406], [0.222488403, 0.716873169, 0.060607910], [0.013916016, 0.097076416, 0.714096069]]
D50 = (0.9642, 1.0, 0.8249)


def srgb_decode(v):
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def srgb_encode(v):
    v = min(max(v, 0.0), 1.0)
    return v * 12.92 if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055


def rgb_to_xyz(rgb):
    lin = [srgb_decode(c) for c in rgb]
    return [sum(SRGB_TO_XYZ[r][c] * lin[c] for c in range(3)) for r in range(3)]


def xyz_to_rgb(xyz):
    m = SRGB_TO_XYZ
    det = (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0]) + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
    inv = [[(m[1][1] * m[2][2] - m[1][2] * m[2][1]) / det, (m[0][2] * m[2][1] - m[0][1] * m[2][2]) / det, (m[0][1] * m[1][2] - m[0][2] * m[1][1]) / det],
           [(m[1][2] * m[2][0] - m[1][0] * m[2][2]) / det, (m[0][0] * m[2][2] - m[0][2] * m[2][0]) / det, (m[0][2] * m[1][0] - m[0][0] * m[1][2]) / det],
           [(m[1][0] * m[2][1] - m[1][1] * m[2][0]) / det, (m[0][1] * m[2][0] - m[0][0] * m[2][1]) / det, (m[0][0] * m[1][1] - m[0][1] * m[1][0]) / det]]
    return [srgb_encode(sum(inv[r][c] * xyz[c] for c in range(3))) for r in range(3)]


def lab_f(t):
    return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116


def xyz_to_lab_encoded(xyz):
    fx, fy, fz = (lab_f(xyz[i] / D50[i]) for i in range(3))
    lab = (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))
    return [min(max(lab[0] / 100, 0), 1), min(max((lab[1] + 128) / 255, 0), 1), min(max((lab[2] + 128) / 255, 0), 1)]


def lab_encoded_to_xyz(lab):
    l, a, b = lab[0] * 100, lab[1] * 255 - 128, lab[2] * 255 - 128
    fy = (l + 16) / 116
    fx, fz = fy + a / 500, fy - b / 200
    inv = lambda f: f ** 3 if f ** 3 > 0.008856 else (f - 16 / 116) / 7.787
    return [inv(fx) * D50[0], inv(fy) * D50[1], inv(fz) * D50[2]]


def grid(points, channels, fn, width):
    """A CLUT, the last input channel varying fastest, `fn` mapping inputs to outputs in 0..1."""
    out = b""
    top = 255 if width == 1 else 65535

    def walk(prefix):
        nonlocal out
        if len(prefix) == channels:
            for v in fn([p / (points - 1) for p in prefix]):
                q = int(round(min(max(v, 0.0), 1.0) * top))
                out += struct.pack(">B" if width == 1 else ">H", q)
            return
        for p in range(points):
            walk(prefix + [p])
    walk([])
    return out


def table(entries, fn, width):
    top = 255 if width == 1 else 65535
    return b"".join(struct.pack(">B" if width == 1 else ">H", int(round(min(max(fn(i / (entries - 1)), 0.0), 1.0) * top))) for i in range(entries))


def mft(kind, inputs, outputs, points, entries_in, entries_out, in_fn, clut_fn, out_fn):
    width = 1 if kind == b"mft1" else 2
    identity = [1, 0, 0, 0, 1, 0, 0, 0, 1]
    data = kind + b"\0\0\0\0" + struct.pack(">BBBB", inputs, outputs, points, 0) + b"".join(s15(v) for v in identity)
    if width == 2:
        data += struct.pack(">HH", entries_in, entries_out)
    for _ in range(inputs):
        data += table(entries_in, in_fn, width)
    data += grid(points, inputs, clut_fn, width)
    for _ in range(outputs):
        data += table(entries_out, out_fn, width)
    return data


def lut_ab(kind, inputs, outputs, b_curves, matrix, m_curves, clut, a_curves):
    """An mAB or mBA tag: offsets to B curves, matrix, M curves, CLUT and A curves."""
    head = 32
    body = b""
    offsets = []
    for part in (b_curves, matrix, m_curves, clut, a_curves):
        if part is None:
            offsets.append(0)
            continue
        offsets.append(head + len(body))
        body += pad4(part)
    return kind + b"\0\0\0\0" + struct.pack(">BBH", inputs, outputs, 0) + struct.pack(">IIIII", *offsets) + body


def curves(*tags):
    return b"".join(pad4(t) for t in tags)


def clut_block(points, channels, fn, width):
    return bytes(points[:channels] + [0] * (16 - channels)) + struct.pack(">BBBB", width, 0, 0, 0) + grid(points[0], channels, fn, width)


def matrix12(values):
    return b"".join(s15(v) for v in values)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    colorants = [xyz_tag(*[SRGB_TO_XYZ[r][c] for r in range(3)]) for c in range(3)]
    rgb_tags = [(b"rXYZ", colorants[0]), (b"gXYZ", colorants[1]), (b"bXYZ", colorants[2])]
    srgb_para = para(3, [2.4, 1 / 1.055, 0.055 / 1.055, 1 / 12.92, 0.04045])
    chad = b"sf32\0\0\0\0" + b"".join(s15(v) for v in [1.0479, 0.0229, -0.0502, 0.0296, 0.9904, -0.0171, -0.0092, 0.0151, 0.7519])
    files = {}

    files["para-types.icc"] = profile(b"RGB ", b"XYZ ", rgb_tags + [
        (b"rTRC", para(0, [2.2])),
        (b"gTRC", srgb_para),
        (b"bTRC", para(4, [2.4, 1 / 1.055, 0.055 / 1.055, 1 / 12.92, 0.04045, 0.001, 0.002])),
        (b"wtpt", xyz_tag(0.9642, 1.0, 0.8249)),
        (b"chad", chad),
        (b"cicp", b"cicp\0\0\0\0" + bytes([12, 13, 0, 1])),
    ])
    # Types 1 and 2 put d at -b/a, which skcms requires to be at least 0.
    files["para-types-12.icc"] = profile(b"RGB ", b"XYZ ", rgb_tags + [(b"rTRC", para(1, [2.2, 1.0, 0.0])), (b"gTRC", para(2, [2.2, 1.1, -0.1, 0.05])), (b"bTRC", para(1, [2.4, 1.0, -0.05]))])
    files["bad-para-negative-d.icc"] = profile(b"RGB ", b"XYZ ", rgb_tags + [(b"rTRC", para(1, [2.4, 1 / 1.055, 0.055 / 1.055])), (b"gTRC", srgb_para), (b"bTRC", srgb_para)])
    files["curv-gamma.icc"] = profile(b"RGB ", b"XYZ ", rgb_tags + [(b"rTRC", curv_gamma(1.8)), (b"gTRC", curv([])), (b"bTRC", curv_gamma(2.2)), (b"cicp", b"cicp\0\0\0\0" + bytes([12, 13, 0, 1]))], version=0x02100000)
    files["gray-ktrc.icc"] = profile(b"GRAY", b"XYZ ", [(b"kTRC", curv([int(round(srgb_decode(i / 1023) * 65535)) for i in range(1024)])), (b"wtpt", xyz_tag(0.9642, 1.0, 0.8249))])
    files["identity-tables.icc"] = profile(b"RGB ", b"XYZ ", rgb_tags + [(b"rTRC", curv([int(round(i / 255 * 65535)) for i in range(256)]))] * 1 + [(b"gTRC", curv([0, 65535])), (b"bTRC", curv([int(round(i / 4095 * 65535)) for i in range(4096)]))])

    a2b = mft(b"mft2", 3, 3, 9, 256, 256, srgb_decode, lambda rgb: xyz_to_lab_encoded(rgb_to_xyz(rgb)), lambda v: v)
    b2a = mft(b"mft2", 3, 3, 9, 256, 256, lambda v: v, lambda lab: xyz_to_rgb(lab_encoded_to_xyz(lab)), lambda v: v)
    files["mft2-lab.icc"] = profile(b"RGB ", b"Lab ", [(b"A2B0", a2b), (b"B2A0", b2a), (b"wtpt", xyz_tag(0.9642, 1.0, 0.8249))])

    def cmyk_to_lab(cmyk):
        c, m, y, k = cmyk
        rgb = [(1 - c) * (1 - k), (1 - m) * (1 - k), (1 - y) * (1 - k)]
        return xyz_to_lab_encoded(rgb_to_xyz(rgb))

    def lab_to_cmyk(lab):
        rgb = xyz_to_rgb(lab_encoded_to_xyz(lab))
        k = 1 - max(rgb)
        if k >= 1:
            return [0, 0, 0, 1]
        return [(1 - rgb[0] - k) / (1 - k), (1 - rgb[1] - k) / (1 - k), (1 - rgb[2] - k) / (1 - k), k]
    a2b = mft(b"mft1", 4, 3, 3, 256, 256, lambda v: v, cmyk_to_lab, lambda v: v)
    b2a = mft(b"mft1", 3, 4, 5, 256, 256, lambda v: v, lab_to_cmyk, lambda v: v)
    files["mft1-cmyk.icc"] = profile(b"CMYK", b"Lab ", [(b"A2B0", a2b), (b"B2A0", b2a)], cls=b"prtr")

    # mAB: A curves (para 3), an 8-bit 5-point CLUT of sRGB's gamma-encoded colors to linear
    # ones, M curves (identity gamma), the sRGB matrix (PCS XYZ encoding), B curves (gamma 1).
    a_curves = curves(srgb_para, srgb_para, srgb_para)
    clut = clut_block([5, 5, 5], 3, lambda rgb: [srgb_encode(v) for v in rgb], 1)
    m_curves = curves(para(0, [2.4]), para(0, [2.4]), para(0, [2.4]))
    enc = 32768 / 65535
    matrix = matrix12([SRGB_TO_XYZ[r][c] * enc for r in range(3) for c in range(3)] + [0.0, 0.001, 0.0])
    b_curves = curves(para(0, [1.0]), curv([]), para(0, [1.0]))
    a2b = lut_ab(b"mAB ", 3, 3, b_curves, matrix, m_curves, clut, a_curves)
    # mBA: B curves, matrix (XYZ to linear sRGB), M curves (sRGB's inverse), 16-bit CLUT
    # (identity), A curves (identity tables of 2 entries).
    inv = [[3.1338561, -1.6168667, -0.4906146], [-0.9787684, 1.9161415, 0.0334540], [0.0719453, -0.2289914, 1.4052427]]
    matrix = matrix12([inv[r][c] * (65535 / 32768) for r in range(3) for c in range(3)] + [0.0, 0.0, 0.0])
    m_curves = curves(*[para(3, [1 / 2.4, 1.055 ** 2.4, 0.0, 12.92, 0.0031308])] * 3)
    clut = clut_block([3, 3, 3], 3, lambda rgb: rgb, 2)
    a2b_curves = curves(curv([0, 65535]), curv([0, 65535]), curv([0, 65535]))
    b2a = lut_ab(b"mBA ", 3, 3, curves(curv([]), curv([]), curv([])), matrix, m_curves, clut, a2b_curves)
    files["mab-xyz.icc"] = profile(b"RGB ", b"XYZ ", [(b"A2B0", a2b), (b"B2A0", b2a), (b"wtpt", xyz_tag(0.9642, 1.0, 0.8249))])

    good = files["para-types.icc"]
    files["bad-signature.icc"] = good[:36] + b"acsq" + good[40:]
    files["bad-illuminant.icc"] = profile(b"RGB ", b"XYZ ", rgb_tags + [(b"rTRC", srgb_para), (b"gTRC", srgb_para), (b"bTRC", srgb_para)], illuminant=(0.9505, 1.0, 1.089))
    files["bad-version.icc"] = good[:8] + struct.pack(">I", 0x05000000) + good[12:]
    files["bad-tag-past-end.icc"] = good[:132 + 4] + struct.pack(">I", len(good) - 8) + struct.pack(">I", 64) + good[132 + 12:]
    files["bad-para.icc"] = profile(b"RGB ", b"XYZ ", rgb_tags + [(b"rTRC", para(1, [2.2, 0.0, 0.1])), (b"gTRC", srgb_para), (b"bTRC", srgb_para)])
    one_point = b"\x01" + clut_block([5, 5, 5], 3, lambda rgb: rgb, 1)[1:]
    files["bad-clut.icc"] = profile(b"RGB ", b"XYZ ", [(b"A2B0", lut_ab(b"mAB ", 3, 3, b_curves, None, None, one_point, a_curves))])

    for name, data in sorted(files.items()):
        (OUT / name).write_bytes(data)
        print(name, len(data))


if __name__ == "__main__":
    main()
