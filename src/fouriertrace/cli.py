"""Command line: fouriertrace IMAGE [options]"""

from __future__ import annotations

import argparse
import os

import cv2

from . import animate, export
from .centerline import trace_centerlines
from .contours import find_curves, join_curves, load_binary, resample, to_math_coords
from .fourier import fourier_series, reconstruction_error


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="fouriertrace",
        description="Turn the curves in an image into complex Fourier series (epicycles).",
    )
    p.add_argument("image", help="input image (PNG/JPG; transparent PNGs use the alpha channel)")
    p.add_argument("-o", "--out", default="out", help="output folder (default: out)")
    p.add_argument("-t", "--terms", type=int, default=100,
                   help="Fourier terms to keep per curve, biggest first (default: 100)")
    p.add_argument("-n", "--samples", type=int, default=1024,
                   help="points sampled along each curve before the FFT (default: 1024)")
    p.add_argument("--join", action="store_true",
                   help="chain all curves into one path -> a single series for the whole image")
    p.add_argument("-c", "--centerline", action="store_true",
                   help="follow the middle of drawn lines, straight through crossings "
                        "(for line drawings and self-crossing curves like kolams)")
    p.add_argument("--holes", action="store_true", help="also trace inner outlines (holes)")
    p.add_argument("--max-curves", type=int, default=20, help="keep at most this many curves, largest first")
    p.add_argument("--min-length", type=float, default=40, help="ignore outlines shorter than this (pixels)")
    p.add_argument("--threshold", type=int, help="fixed 0-255 threshold instead of automatic (Otsu)")
    p.add_argument("--invert", action="store_true", default=None,
                   help="treat light pixels as the drawing (auto-detected if omitted)")
    p.add_argument("--pixels", action="store_true",
                   help="keep pixel units (y flipped) instead of normalising to [-1, 1]")
    p.add_argument("--animate", nargs="?", const="epicycles.gif", metavar="FILE",
                   help="also render an epicycle animation (default name: epicycles.gif; .mp4 needs ffmpeg)")
    p.add_argument("-p", "--print", dest="print_fmt", nargs="?", const="complex",
                   choices=sorted(export.FORMATS), metavar="FORMAT",
                   help="print the equation(s) to the terminal: complex (default), xy, desmos or latex")
    p.add_argument("--digits", type=int, default=4, help="decimal places in printed equations (default: 4)")
    p.add_argument("--frames", type=int, default=240, help="animation frames (default: 240)")
    p.add_argument("--circles", type=int, default=60, help="circles drawn per curve in the animation")
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    os.makedirs(args.out, exist_ok=True)

    mask = load_binary(args.image, invert=args.invert, threshold=args.threshold)
    h, w = mask.shape
    if args.centerline:
        curves = trace_centerlines(mask, min_length=args.min_length)[: args.max_curves]
    else:
        curves = find_curves(mask, min_length=args.min_length, holes=args.holes)[: args.max_curves]
    if not curves:
        raise SystemExit("No curves found. Try --invert, --threshold or a lower --min-length.")
    curves = to_math_coords(curves, w, h, normalize=not args.pixels)
    if args.join:
        curves = [join_curves(curves)]

    samples = [resample(z, args.samples) for z in curves]
    series = [fourier_series(z, args.terms) for z in samples]

    export.write_json(series, os.path.join(args.out, "coefficients.json"))
    export.write_csv(series, os.path.join(args.out, "coefficients.csv"))
    export.write_desmos(series, os.path.join(args.out, "desmos.txt"))
    with open(os.path.join(args.out, "equations.tex"), "w") as f:
        for i, s in enumerate(series):
            f.write(f"% curve {i}\n{export.latex_complex(s)}\n\n")
    cv2.imwrite(os.path.join(args.out, "mask.png"), mask)
    animate.save_preview(samples, series, os.path.join(args.out, "preview.png"))

    print(f"{len(series)} curve(s), {args.terms} terms each -> {args.out}/")
    for i, (s, z) in enumerate(zip(series, samples)):
        err = reconstruction_error(s, z)
        print(f"  curve {i}: mean error {err:.4g} ({'pixels' if args.pixels else 'of half-width'})")

    if args.print_fmt:
        print(f"\nEquation{'s' if len(series) > 1 else ''} ({args.print_fmt}, 0 <= t < 2*pi):")
        for i, s in enumerate(series):
            if len(series) > 1:
                print(f"\n# curve {i}")
            print(export.format_equation(s, args.print_fmt, args.digits))

    if args.animate:
        path = os.path.join(args.out, args.animate)
        animate.save_animation(series, path, frames=args.frames, max_circles=args.circles)
        print(f"  animation -> {path}")


if __name__ == "__main__":
    main()
