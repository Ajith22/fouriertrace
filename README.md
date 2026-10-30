# fouriertrace

![tests](https://github.com/Ajith22/fouriertrace/actions/workflows/tests.yml/badge.svg)
![python](https://img.shields.io/badge/python-3.9%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)

**Give it an image with simple curves. Get back the Fourier series that draws it.**

fouriertrace traces the outlines in a picture and writes each one as a sum of spinning circles (epicycles). You get the equation printed in your terminal, the coefficients as data, a version you can paste into Desmos, and an animation of the circles drawing your image.

![Epicycles drawing a heart and a star](docs/demo.gif)

---

## Contents

- [Quick start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
- [Output files](#output-files)
- [Using it from Python](#using-it-from-python)
- [How it works](#how-it-works)
- [Tips and limitations](#tips-and-limitations)
- [Inspiration and credits](#inspiration-and-credits)
- [Contributing](#contributing)
- [License](#license)

---

## Quick start

```bash
git clone https://github.com/Ajith22/fouriertrace.git
cd fouriertrace
pip install -e .

python examples/make_examples.py                          # make two sample images
fouriertrace examples/heart_star.png -t 6 --print --animate
```

That prints an equation for each shape and saves an epicycle animation to `out/epicycles.gif`.

---

## Installation

You need **Python 3.9 or newer**.

```bash
git clone https://github.com/Ajith22/fouriertrace.git
cd fouriertrace

# optional but recommended: a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -e .
```

This installs the `fouriertrace` command and its dependencies (NumPy, OpenCV, Matplotlib, Pillow). To save animations as MP4 instead of GIF you also need [ffmpeg](https://ffmpeg.org/) on your PATH.

---

## Usage

```bash
fouriertrace IMAGE [options]
```

### Common recipes

```bash
fouriertrace drawing.png                       # one series per curve, files written to out/
fouriertrace drawing.png -t 10 --print         # print a short equation in the terminal
fouriertrace drawing.png -p xy                 # print as x(t) and y(t)
fouriertrace drawing.png -p desmos             # print a line you can paste into Desmos
fouriertrace drawing.png -t 200 --animate      # more detail + epicycles.gif
fouriertrace kolam.png -c -t 60 --animate      # line drawing that crosses itself
fouriertrace drawing.png --join -p             # ONE equation for the whole image
fouriertrace logo.png --invert                 # light drawing on a dark background
fouriertrace drawing.png --animate demo.mp4    # MP4 instead of GIF (needs ffmpeg)
```

### Outlines vs. centerlines

There are two ways to turn ink into a curve:

| Mode | Follows | Use it for |
|---|---|---|
| outline (default) | the **edge** of each filled shape | silhouettes, logos, icons, filled shapes |
| `-c, --centerline` | the **middle** of each drawn line, going straight through every crossing | line drawings, signatures, kolams, figure-8s, anything drawn with a pen |

With a self-crossing line drawing, outline mode only finds the outer boundary, because the crossings join everything into one blob. Centerline mode thins the line to its middle, then walks it like a pen: at every crossing it carries straight on. A single continuous drawing comes out as **one** equation.

Open strokes (a line with two loose ends) are traced out and back, since a Fourier series has to be a closed loop.

### Printing the equation

`--print` (or `-p`) writes the series to the terminal. Fewer terms (`-t`) give a shorter, smoother equation; more terms give a sharper but longer one.

```console
$ fouriertrace examples/heart_star.png -t 6 --print
2 curve(s), 6 terms each -> out/
  curve 0: mean error 0.005587 (of half-width)
  curve 1: mean error 0.02191 (of half-width)

Equations (complex, 0 <= t < 2*pi):

# curve 0
z(t) = (0.4489 - 0.0001i) + 0.3258·e^(i(t + 1.5697)) + 0.0776·e^(i(-4t + 1.5737)) + 0.0347·e^(i(6t + 1.5638)) + ...
```

Read each term `r·e^(i(nt + φ))` as one circle: radius `r`, spinning `n` times per loop (negative means clockwise), starting at angle `φ` radians. The first bracket is the centre point.

| Format | Looks like | Good for |
|---|---|---|
| `complex` (default) | `z(t) = c₀ + r·e^(i(nt + φ)) + …` | understanding the epicycles |
| `xy` | `x(t) = Σ r·cos(nt + φ)` and `y(t) = Σ r·sin(nt + φ)` | plotting tools, calculators, code |
| `desmos` | `\left(…, …\right)` | pasting into [Desmos](https://www.desmos.com/calculator); set `0 ≤ t ≤ 2π` |
| `latex` | `z(t) = (a+bi)e^{nit} + …` | papers and slides |

### All options

| Option | Default | What it does |
|---|---|---|
| `-o, --out DIR` | `out` | folder for the output files |
| `-t, --terms N` | `100` | Fourier terms kept per curve, largest circles first |
| `-p, --print [FORMAT]` | off | print the equation(s): `complex`, `xy`, `desmos` or `latex` |
| `--digits N` | `4` | decimal places in printed equations |
| `-n, --samples N` | `1024` | points sampled along each curve before the FFT |
| `--join` | off | chain every curve into one path, giving a single series (the jumps between shapes get drawn too) |
| `-c, --centerline` | off | follow the middle of drawn lines, straight through crossings (see above) |
| `--holes` | off | also trace inner outlines, such as the inside of an "O" (outline mode) |
| `--max-curves N` | `20` | keep at most N curves, largest first |
| `--min-length PX` | `40` | ignore outlines shorter than this, in pixels (removes specks) |
| `--invert` | auto | treat light pixels as the drawing |
| `--threshold 0-255` | auto (Otsu) | fixed brightness cut-off instead of automatic |
| `--pixels` | off | keep pixel units instead of scaling the image to [-1, 1] |
| `--animate [FILE]` | off | render the epicycle animation (`epicycles.gif` if no name given) |
| `--frames N` | `240` | animation length in frames |
| `--circles N` | `60` | circles drawn per curve in the animation (the rest still count, they're just not drawn) |

Run `fouriertrace --help` for the same list in your terminal.

---

## Output files

Everything goes into the `--out` folder (default `out/`):

| File | Contents |
|---|---|
| `coefficients.json` | every term of every curve: `n`, real and imaginary parts, radius, phase |
| `coefficients.csv` | the same data as a spreadsheet, one row per term |
| `desmos.txt` | one parametric equation per curve, ready for Desmos |
| `equations.tex` | the series written out in LaTeX |
| `preview.png` | the reconstructed curves drawn over the original outline, to check the fit |
| `mask.png` | the black-and-white image that was traced, useful when the result looks wrong |
| `epicycles.gif` | the animation, if you used `--animate` |

---

## Using it from Python

```python
from fouriertrace import load_binary, find_curves, to_math_coords, resample, fourier_series
from fouriertrace.export import format_equation

mask = load_binary("drawing.png")                       # image -> black/white mask
h, w = mask.shape
curves = to_math_coords(find_curves(mask), w, h)        # outlines as complex numbers
series = fourier_series(resample(curves[0], 1024), terms=20)

print(format_equation(series, "xy"))                    # the equation as text

for term in series.sorted_for_drawing()[:5]:            # the biggest circles
    print(term.n, term.radius, term.phase)

import numpy as np
points = series(np.linspace(0, 2 * np.pi, 500))         # evaluate the curve anywhere
```

---

## How it works

1. **Trace.** The image is turned into a black-and-white mask (automatic Otsu threshold, or the alpha channel of a transparent PNG). In outline mode, OpenCV traces the edge of every shape. In centerline mode, the ink is thinned to a 1-pixel skeleton (scikit-image), the pixels around each crossing are merged into one point, and the skeleton is walked like a pen, going straight through each crossing.
2. **Treat points as complex numbers.** Each point `(x, y)` on an outline becomes `z = x + iy`, so a closed outline becomes a looping function `z(t)` for `t` from 0 to 2π. The outline is resampled so the points are evenly spaced along it.
3. **Fourier transform.** A Fast Fourier Transform breaks the loop into circles:

   $$z(t) = \sum_n c_n \, e^{int}$$

   Each coefficient $c_n$ is one circle with radius $|c_n|$ and starting angle $\arg c_n$, turning $n$ times per loop. Chaining the circles tip-to-tail traces the original shape.
4. **Keep the biggest circles.** Only the `--terms` largest circles are kept. Small numbers of terms give smooth, rounded versions; more terms reproduce sharp corners.
5. **Export.** The kept terms are written as data, equations, a preview, and optionally an animation.

---

## Tips and limitations

- **Use high-contrast images:** dark shapes on a light background, light on dark with `--invert`, or a transparent PNG. Check `mask.png` if the result looks odd, and adjust `--threshold`.
- **For line drawings, use `--centerline`.** Without it, a drawn line is traced around its outside edge, and a line that crosses itself shows only its outer boundary.
- **Centerline mode likes clean lines.** Lines of fairly even thickness that cross cleanly work best. Small dots or specks are ignored (raise `--min-length` to ignore bigger ones). Where three or more lines meet at one point, the pen picks the straightest way through, which may not be how it was drawn.
- **Hand-drawn lines are slightly wobbly**, and with many terms the series reproduces the wobble. Fewer terms (`-t 40` to `-t 80`) give a smoother curve.
- **Sharp corners need many terms.** Square corners always overshoot slightly (the Gibbs phenomenon); raising `-t` makes it smaller.
- **`--join` draws connecting lines** between separate shapes, because a single equation has to travel from one shape to the next.
- Photos and shaded images don't work well: the tool is meant for silhouettes, logos, icons and line art.

---

## Inspiration and credits

**The idea.** Drawing pictures with chains of spinning circles was made famous by Grant Sanderson's 3Blue1Brown video [*But what is a Fourier series? From heat flow to drawing with circles*](https://www.3blue1brown.com/lessons/fourier-series) (2019). This project exists because of that video: the maths, the "circles on circles" picture and the look of the animation all follow it.

**Related projects that inspired the features:**
- Daniel Shiffman's Coding Train [Coding Challenge #130: Drawing with Fourier Transform and Epicycles](https://thecodingtrain.com/challenges/130-drawing-with-fourier-transform-and-epicycles), which implements the same idea in p5.js for hand-drawn and SVG paths.
- Jack Finnis's [Fourier](https://apps.apple.com/us/app/fourier/id1582827502) app for iPhone and iPad, which turns silhouettes and SVGs into epicycles and exports the coefficients. fouriertrace aims at the same goal as an open-source command-line tool that also handles several curves per image and prints the equation.

**The history.** Epicycles go back to ancient Greek astronomy (Hipparchus and Ptolemy used circles on circles to model planetary motion). Joseph Fourier introduced Fourier series in his work on heat flow in the early 1800s.

**What this code is.** fouriertrace was written from scratch for this repository; no code was copied from the projects above. It was built with help from Claude (Anthropic's AI assistant). It stands on these open-source libraries:
- [NumPy](https://numpy.org/) for the FFT and maths
- [OpenCV](https://opencv.org/) for thresholding and contour tracing
- [scikit-image](https://scikit-image.org/) for skeletonizing line drawings
- [Matplotlib](https://matplotlib.org/) and [Pillow](https://python-pillow.org/) for previews and animations

---

## Contributing

Issues and pull requests are welcome. To set up a development copy:

```bash
pip install -e ".[dev]"
pytest
```

Tests run automatically on GitHub Actions for every push. Ideas for next steps: SVG input and a web version.

---

## License

[MIT](LICENSE) © 2026 Ajith Kumar
