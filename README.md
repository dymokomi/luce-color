# luce-color

Perceptual color for user interfaces, written in Luce Base. A theme names a
handful of base surfaces; the hover, focus and active-line variants a UI needs
are *derived* from them here, so a palette can never fall out of step with
itself. A grayscale palette yields grayscale states; a tinted one stays in its
own hue family.

Work happens in [Oklab](https://bottosson.github.io/posts/oklab/), where equal
numeric steps look like equal steps to the eye, so a lift or a blend lands where
you expect regardless of the starting color.

## Model

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
