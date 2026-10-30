import numpy as np
import cv2

from fouriertrace import find_curves, fourier_series, join_curves, reconstruction_error, resample
from fouriertrace.export import desmos_expression, format_equation


def test_circle_is_one_term():
    t = 2 * np.pi * np.arange(256) / 256
    z = 0.5 + 0.25j + 2.0 * np.exp(1j * t)  # circle radius 2, centred at 0.5+0.25i
    s = fourier_series(z, terms=1)
    nonconst = [term for term in s.terms if term.n != 0]
    assert len(nonconst) == 1 and nonconst[0].n == 1
    assert abs(nonconst[0].radius - 2.0) < 1e-9
    const = [term for term in s.terms if term.n == 0][0]
    assert abs(const.c - (0.5 + 0.25j)) < 1e-9


def test_clockwise_circle_has_negative_frequency():
    t = 2 * np.pi * np.arange(128) / 128
    s = fourier_series(np.exp(-1j * t), terms=1)
    assert [term.n for term in s.terms if term.n != 0] == [-1]


def test_square_reconstructs_well():
    corners = np.array([1 + 1j, -1 + 1j, -1 - 1j, 1 - 1j])
    edges = [np.linspace(a, b, 50, endpoint=False) for a, b in zip(corners, np.roll(corners, -1))]
    z = resample(np.concatenate(edges), 512)
    assert reconstruction_error(fourier_series(z, terms=100), z) < 0.02
    assert reconstruction_error(fourier_series(z, terms=4), z) > reconstruction_error(fourier_series(z, terms=100), z)


def test_resample_is_evenly_spaced():
    z = np.array([0, 10, 10 + 1j, 1j])  # thin rectangle with very uneven input spacing
    r = resample(z, 220)
    gaps = np.abs(np.diff(np.append(r, r[0])))
    assert np.allclose(gaps, gaps.mean(), rtol=1e-6)


def test_find_curves_on_drawn_shapes():
    img = np.zeros((200, 300), np.uint8)
    cv2.circle(img, (70, 100), 50, 255, -1)
    cv2.rectangle(img, (170, 50), (270, 150), 255, -1)
    curves = find_curves(img)
    assert len(curves) == 2
    joined = join_curves(curves)
    assert len(joined) == sum(len(c) for c in curves)


def test_desmos_expression_shape():
    t = 2 * np.pi * np.arange(64) / 64
    expr = desmos_expression(fourier_series(np.exp(1j * t) + np.exp(-2j * t), terms=2))
    assert expr.startswith("\\left(") and expr.endswith("\\right)")
    assert "\\cos(1t" in expr and "\\sin(-2t" in expr


def test_printed_equations_for_a_circle():
    t = 2 * np.pi * np.arange(64) / 64
    s = fourier_series(1 + 2 * np.exp(1j * (t + 0.5)), terms=1)
    assert format_equation(s, "complex") == "z(t) = (1 + 0i) + 2·e^(i(t + 0.5))"
    assert format_equation(s, "xy") == "x(t) = 1 + 2·cos(t + 0.5)\ny(t) = 0 + 2·sin(t + 0.5)"


def test_centerline_follows_a_figure_eight_through_its_crossing():
    from fouriertrace.centerline import trace_centerlines

    t = np.linspace(0, 2 * np.pi, 800, endpoint=False)
    x = 200 + 150 * np.sin(t)
    y = 150 + 90 * np.sin(t) * np.cos(t)  # lemniscate: crosses itself at (200, 150)
    img = np.zeros((300, 400), np.uint8)
    cv2.polylines(img, [np.stack([x, y], 1).astype(np.int32)], True, 255, 7)

    paths = trace_centerlines(img)
    assert len(paths) == 1                                  # one pen stroke, not two outlines
    z = paths[0]
    assert np.abs(z - (200 + 150j)).min() < 5               # goes through the crossing
    true_len = np.abs(np.diff(np.append(x + 1j * y, x[0] + 1j * y[0]))).sum()
    assert abs(np.abs(np.diff(z)).sum() / true_len - 1) < 0.1

    # outline tracing, by contrast, only sees the outer edge
    assert len(find_curves(img)) == 1
