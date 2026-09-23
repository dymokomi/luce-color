# luce-color

Colour science for Luce, written in Luce Base. Everything that turns numbers
into colours and colours into what the eye sees lives here, so an editor, a
UI theme and a file codec agree about what a colour is:

| module | what it holds |
| --- | --- |
| `color` | `Color` (linear sRGB, the GPU model), Oklab, and the surface derivations luce-ui themes use (`elevate`, `blend`) |
| `transfer` | transfer functions: sRGB, gamma 1.8/2.2/2.4, PQ (ST 2084), HLG; `encode`/`decode` by `Transfer` |
| `xyz` | CIE XYZ, chromaticities and whites (D65, D50, ACES), `Primaries` for sRGB, Display P3, Adobe RGB, Rec. 2020, ACES AP0/AP1, ProPhoto; matrices *derived* from chromaticities; Bradford adaptation; `convert` between primaries |
| `lab` | CIELAB and LCh against any white, ΔE76 and CIEDE2000, OkLCh |
| `cam16` | CAM16 viewing conditions, appearance (J, Q, C, M, s, h), the inverse from JCh, CAM16-UCS and its ΔE |
| `oklab` | Oklab from XYZ, ΔEok, sRGB `max_chroma(l, h)`, CSS-style gamut mapping by chroma reduction (`to_srgb`), gamut-relative chroma for pickers |
| `hsl` | HSV (Photoshop's HSB) and HSL over encoded RGB, for pickers |
| `space` | `ColorSpace` = name + primaries + transfer, as OpenColorIO models one; a catalogue (`space.all`, `space.named`); `convert(color, from, to)` — decode, matrix, adapt, matrix, encode — plus `to_lab`, `to_oklab_in`, `to_appearance`, `in_gamut`, `clamp` |

```luce
import space
import lab
import cam16

# Display P3's red, as sRGB sees it: out of gamut, so clamp for a preview.
let red = space.convert(color.Color(1.0, 0.0, 0.0), space.display_p3, space.srgb)
let shown = space.clamp(red)

# How different are two paints? CIEDE2000 about 1 is a just-noticeable step.
let difference = lab.delta_e2000(space.to_lab(a, space.srgb), space.to_lab(b, space.srgb))

# What a colour looks like on this display: CAM16 lightness, chroma and hue.
let look = space.to_appearance(a, space.srgb, space.display_viewing(space.srgb))
```

Numbers are checked against the published references in each module's tests:
the sRGB matrix, ST 2084's luminance anchors, Sharma's CIEDE2000 pairs, CAM16's
white and inverse. An OCIO config reader is not here yet; `space.convert` is the
processor chain one would produce for a pair of its colour spaces.

## Theme derivations (`color`)

`Color` is a linear-light sRGB triple — the same model as `gpu.Color` — so a
caller bridges with a field-wise copy and no gamma handling of its own. `Oklab`
is the perceptual space: lightness `l` with opponent axes `a` and `b`, both zero
for a neutral gray.

```luce
import color

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
./test.sh
```

Licensed under either of Apache-2.0 or MIT at your option.
