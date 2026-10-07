# luce-color

Color science for Luce, written in Luce Base. Everything that turns numbers
into colors and colors into what the eye sees lives here, so an editor, a
UI theme and a file codec agree about what a color is:

| module | what it holds |
| --- | --- |
| `color` | `Color` (linear sRGB, the GPU model), Oklab, and the surface derivations luce-ui themes use (`elevate`, `blend`) |
| `transfer` | transfer functions: sRGB, gamma 1.8/2.2/2.4, PQ (ST 2084), HLG; `encode`/`decode` by `Transfer`; for per-pixel CPU loops `srgb_byte` and `SrgbTable` (the decoding interpolated from 4097 samples) |
| `xyz` | CIE XYZ, chromaticities and whites (D65, D50, ACES), `Primaries` for sRGB, Display P3, Adobe RGB, Rec. 2020, ACES AP0/AP1, ProPhoto; matrices *derived* from chromaticities; Bradford adaptation; `convert` between primaries |
| `lab` | CIELAB and LCh against any white, ΔE76 and CIEDE2000, OkLCh |
| `cam16` | CAM16 viewing conditions, appearance (J, Q, C, M, s, h), the inverse from JCh, CAM16-UCS and its ΔE |
| `oklab` | Oklab from XYZ, ΔEok, sRGB `max_chroma(l, h)`, CSS-style gamut mapping by chroma reduction (`to_srgb`), gamut-relative chroma for pickers |
| `hsl` | HSV (Photoshop's HSB) and HSL over encoded RGB, for pickers |
| `space` | `ColorSpace` = name + primaries + transfer, as OpenColorIO models one; a catalogue (`space.all`, `space.named`); `convert(color, from, to)` — decode, matrix, adapt, matrix, encode — plus `to_lab`, `to_oklab_in`, `to_appearance`, `in_gamut`, `clamp` |
| `aces` | the ACES 2.0 Output Transform: Hellwig 2022 JMh, the Daniele tonescale, chroma compression and gamut compression into a display's limiting gamut, for SDR and HDR peaks, and its inverse; matches OpenColorIO's builtin transforms within 1e-4 of the peak |
| `icc` | ICC profiles, a port of skcms (Skia's ICC library): `parse` (v2 and v4, matrix/TRC, A2B/B2A lookup tables, cicp), transfer functions and curve fitting, `transform` between profiles and pixel formats; Skia's `ColorSpace` (from a profile, CICP code points or named primaries and curves) and the `Steps` between two of them |

```luce
from luce_color import space, lab, cam16

# Display P3's red, as sRGB sees it: out of gamut, so clamp for a preview.
let red = space.convert(color.Color(1.0, 0.0, 0.0), space.display_p3, space.srgb)
let shown = space.clamp(red)

# How different are two paints? CIEDE2000 about 1 is a just-noticeable step.
let difference = lab.delta_e2000(space.to_lab(a, space.srgb), space.to_lab(b, space.srgb))

# What a color looks like on this display: CAM16 lightness, chroma and hue.
let look = space.to_appearance(a, space.srgb, space.display_viewing(space.srgb))
```

The sRGB curve for GLSL shaders is `shaders/srgb.glsl`: luce-painting's and luce-image's
shaders include it (`embed_shaders.py -I ../luce-color/shaders`), so there is one copy.

Numbers are checked against the published references in each module's tests:
the sRGB matrix, ST 2084's luminance anchors, Sharma's CIEDE2000 pairs, CAM16's
white and inverse. An OCIO config reader is not here yet; `space.convert` is the
processor chain one would produce for a pair of its color spaces.

## ACES 2.0 (`aces`)

```luce
from luce_color import aces, xyz

# SDR: a 100-nit display limited to Rec.709/sRGB primaries.
let sdr = try aces.OutputTransform.create(100.0, xyz.srgb)
let shown = sdr.apply_ap1([0.18, 0.18, 0.18])   # ACEScg in; display-linear sRGB-primary RGB out, ~0.1
let scene = sdr.invert_ap1([1.0, 1.0, 1.0])      # display white back to the scene light that shows as white
```

`OutputTransform.create(peak_nits, limiting)` builds the transform's hue tables once,
in a few milliseconds. `apply(ap0)` and `apply_ap1(ap1)` give display-linear RGB in
the limiting primaries, where 1.0 is 100 cd/m² (an SDR display's white is 1.0, a
1000-nit display's is 10.0), clamped to the peak. `to_xyz()` converts that RGB to
CIE XYZ. Encoding for the display is the caller's job, through `space` and
`transfer`. The transform follows the Academy's aces-output and OpenColorIO's ACES2
implementation (reference only), in f64. `tests/aces` compares it with
OpenColorIO 2.6's builtins (SDR Rec.709, SDR P3-D65, 1000-nit P3-D65 and Rec.2020)
on 447 colors each. The largest difference is 1.5e-5 of the peak.
`tests/make_aces_fixtures.py` regenerates the reference from OpenColorIO.

`invert(display)` and `invert_ap1(display)` run the transform backward, as
OpenColorIO's inverse ACES2 output transform does: display-linear RGB to the scene
light the forward transform shows as it. That is how display-referred pictures
(JPEGs, textures, screen captures) enter a scene and still look as they did: put
through the plain sRGB decode instead, their white would sit at scene 1.0 and show
grey. Shown again, the inverse lands on the display color within 2e-4 of the peak
across a grid of SDR colors. Against OpenColorIO's inverse on the same 447 colors,
scene light under ten times reference white agrees within 0.05%. Nearer the peak
the inverse is very steep (display 0.99 is scene 30 to 140). There the two
implementations, shown again, agree within 6e-4 of the peak, and each lands about
that close to the display color.

## ICC profiles (`icc`)

`icc` is a faithful port of skcms, the ICC library Skia (and so Chrome, Android and Ladybird)
uses, with the parts of Skia that make a profile into the color space an image is drawn in.
It computes in f32 in skcms's order without fused multiply-adds, so its results are skcms's
built portable without contraction, to the bit: `tests/icc_oracle` holds every profile of
`tests/fixtures/icc` against skcms's own dump of it, and against Skia's color spaces.

```luce
from luce_color import icc

# A PNG's iCCP profile: what does it make of a pixel, in sRGB?
let profile = icc.parse(profile_bytes) else return
let srgb = icc.Profile.srgb()
_ = icc.transform(pixels, .rgba_8888, .unpremul, &profile, out, .rgba_8888, .unpremul, &srgb, count)

# As Skia draws an image tagged with it: the color space, then the steps to sRGB.
if let space = icc.ColorSpace.from_profile(&profile):
    let destination = icc.ColorSpace.srgb()
    let steps = icc.Steps.make(&space, .premul, &destination, .premul)
    let shown = steps.apply([0.6, 0.0, 0.0, 1.0])

# CICP code points (ITU-T H.273), as a PNG's cICP chunk gives them: Display P3.
let p3 = icc.ColorSpace.cicp(12, 13)
```

| Function | Purpose |
| --- | --- |
| `parse(bytes)`, `parse_with_a2b_priority` | A profile, or none when malformed or unusable (skcms_Parse). |
| `transform(src, format, alpha, profile, dst, ...)` | Pixels between profiles and formats (skcms_Transform). |
| `TransferFunction.kind/eval/invert` | skcms's transfer functions: sRGB-ish, PQ(-ish), HLG(-ish). |
| `Curve.eval/approximate` | A tone curve; a table fitted with a transfer function (skcms_ApproximateCurve). |
| `Profile.make_usable_as_destination` | Tabulated curves replaced by fitted ones. |
| `approximately_equal_profiles(a, b)` | Profiles that move colors alike (skcms_ApproximatelyEqualProfiles). |
| `ColorSpace.from_profile/cicp/rgb` | Skia's SkColorSpace::Make, MakeCICP, MakeRGB. |
| `Steps.make(src, alpha, dst, alpha)` | SkColorSpaceXformSteps; `apply` on one color. |
| `transfer_function(t)`, `primaries_matrix(p)`, `ColorSpace.from_space(s)` | This library's `transfer`, `xyz` and `space` types in skcms's terms. |

skcms and Skia are BSD-3-Clause (LICENSE-skia); the port keeps their notices.

## Theme derivations (`color`)

`Color` is a linear-light sRGB triple — the same model as `gpu.Color` — so a
caller bridges with a field-wise copy and no gamma handling of its own. `Oklab`
is the perceptual space: lightness `l` with opponent axes `a` and `b`, both zero
for a neutral gray.

```luce
from luce_color import color

# A hovered surface: lift a base color toward the foreground in perceptual
# lightness, keeping its hue. amount 0 is the base, 1 the reference lightness.
let hover = color.elevate(color.Color(0.02, 0.03, 0.05), color.Color(0.7, 0.75, 0.82), 0.1)

# A midpoint state, such as a hovered border between resting and focused:
let edge = color.blend(color.Color(0.06, 0.09, 0.12), color.Color(0.10, 0.22, 0.32), 0.5)
```

## Reference

| Function | Purpose |
| --- | --- |
| `to_oklab(color)` | Linear sRGB to Oklab. |
| `to_color(lab)` | Oklab to linear sRGB, clamped to the displayable cube. |
| `elevate(base, reference, amount)` | Shift `base` toward `reference` in lightness only, keeping hue and chroma. |
| `blend(a, b, amount)` | Interpolate two colors in Oklab, so midpoints stay saturated. |

## Build and test

Keep `luce-color`, `luce`, and `luce-base` as sibling checkouts. The tested
compiler revisions are recorded in `bootstrap/`. Build the native compilers,
then run the module's test blocks in every compiled mode:

```sh
(cd ../luce-base && ./build.sh)
(cd ../luce && LUCE_BASE_COMPILER=../luce-base/build/luce-base ./build.sh)
luc test
```

Licensed under either of Apache-2.0 or MIT at your option.
