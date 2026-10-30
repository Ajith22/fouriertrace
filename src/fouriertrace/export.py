"""Write Fourier series out as JSON, CSV, Desmos expressions and LaTeX."""

from __future__ import annotations

import csv
import json

from .fourier import FourierSeries


def _num(x: float, digits: int) -> str:
    s = f"{x:.{digits}f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def to_dict(series_list: list[FourierSeries]) -> dict:
    return {
        "description": "z(t) = sum c_n * exp(i*n*t), t in [0, 2*pi). One entry per curve.",
        "curves": [
            [
                {"n": t.n, "re": t.c.real, "im": t.c.imag, "radius": t.radius, "phase": t.phase}
                for t in s.sorted_for_drawing()
            ]
            for s in series_list
        ],
    }


def write_json(series_list: list[FourierSeries], path: str) -> None:
    with open(path, "w") as f:
        json.dump(to_dict(series_list), f, indent=2)


def write_csv(series_list: list[FourierSeries], path: str) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["curve", "n", "re", "im", "radius", "phase"])
        for i, s in enumerate(series_list):
            for t in s.sorted_for_drawing():
                w.writerow([i, t.n, t.c.real, t.c.imag, t.radius, t.phase])


def desmos_expression(series: FourierSeries, digits: int = 4) -> str:
    """Parametric (x(t), y(t)) in the plain-text form Desmos accepts when pasted.

    Uses c_n e^{int} = r(cos(nt+p) + i sin(nt+p)). Set t from 0 to 2*pi in Desmos.
    """
    xs, ys = [], []
    for t in series.sorted_for_drawing():
        r, p = t.radius, t.phase
        if t.n == 0:
            xs.append(_num(t.c.real, digits))
            ys.append(_num(t.c.imag, digits))
            continue
        arg = f"{t.n}t{'+' if p >= 0 else '-'}{_num(abs(p), digits)}"
        xs.append(f"{_num(r, digits)}\\cos({arg})")
        ys.append(f"{_num(r, digits)}\\sin({arg})")
    join = lambda parts: "+".join(parts).replace("+-", "-")
    return f"\\left({join(xs)},{join(ys)}\\right)"


def write_desmos(series_list: list[FourierSeries], path: str, digits: int = 4) -> None:
    with open(path, "w") as f:
        f.write("% Paste each line into Desmos as its own expression; set 0 <= t <= 2pi.\n")
        for s in series_list:
            f.write(desmos_expression(s, digits) + "\n")


def latex_complex(series: FourierSeries, digits: int = 3) -> str:
    """z(t) = sum of c_n e^{int}, written out term by term."""
    parts = []
    for t in series.sorted_for_drawing():
        c = f"({_num(t.c.real, digits)}{'+' if t.c.imag >= 0 else '-'}{_num(abs(t.c.imag), digits)}i)"
        parts.append(c if t.n == 0 else f"{c}e^{{{t.n}it}}")
    return "z(t) = " + " + ".join(parts)


def _signed_join(parts: list[str]) -> str:
    out = parts[0] if parts else "0"
    for p in parts[1:]:
        out += f" - {p[1:]}" if p.startswith("-") else f" + {p}"
    return out


def _angle(n: int, phase: float, digits: int) -> str:
    nt = "t" if n == 1 else "-t" if n == -1 else f"{n}t"
    p = _num(phase, digits)
    sign, mag = ("-", p[1:]) if p.startswith("-") else ("+", p)
    return f"{nt} {sign} {mag}"


def plain_complex(series: FourierSeries, digits: int = 4) -> str:
    """Readable complex form:  z(t) = c0 + r1·e^(i(n1·t + p1)) + ..."""
    parts = []
    for t in series.sorted_for_drawing():
        if t.n == 0:
            im = _num(t.c.imag, digits)
            sign, mag = ("-", im[1:]) if im.startswith("-") else ("+", im)
            parts.append(f"({_num(t.c.real, digits)} {sign} {mag}i)")
        else:
            parts.append(f"{_num(t.radius, digits)}·e^(i({_angle(t.n, t.phase, digits)}))")
    return "z(t) = " + _signed_join(parts)


def plain_xy(series: FourierSeries, digits: int = 4) -> str:
    """Two real equations:  x(t) = Σ r cos(nt + p),  y(t) = Σ r sin(nt + p)."""
    xs, ys = [], []
    for t in series.sorted_for_drawing():
        if t.n == 0:
            xs.append(_num(t.c.real, digits))
            ys.append(_num(t.c.imag, digits))
        else:
            a = _angle(t.n, t.phase, digits)
            xs.append(f"{_num(t.radius, digits)}·cos({a})")
            ys.append(f"{_num(t.radius, digits)}·sin({a})")
    return f"x(t) = {_signed_join(xs)}\ny(t) = {_signed_join(ys)}"


FORMATS = {
    "complex": plain_complex,
    "xy": plain_xy,
    "desmos": desmos_expression,
    "latex": latex_complex,
}


def format_equation(series: FourierSeries, fmt: str = "complex", digits: int = 4) -> str:
    return FORMATS[fmt](series, digits)
