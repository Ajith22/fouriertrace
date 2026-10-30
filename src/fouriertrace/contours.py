"""Turn an image into one or more closed curves, as complex numbers."""

from __future__ import annotations

import cv2
import numpy as np


def load_binary(path: str, invert: bool | None = None, threshold: int | None = None) -> np.ndarray:
    """Load an image and return a binary mask where the drawing is white (255).

    Transparent PNGs use their alpha channel. Otherwise the image is converted to
    grayscale and thresholded (Otsu by default). If ``invert`` is None we guess:
    the drawing is assumed to be the minority colour.
    """
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {path}")

    if img.ndim == 3 and img.shape[2] == 4 and img[:, :, 3].min() < 255:
        gray = img[:, :, 3]  # alpha: opaque = drawing
        invert = False if invert is None else invert
    else:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img

    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    if threshold is None:
        _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    else:
        _, mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)

    if invert is None:
        invert = np.count_nonzero(mask) > mask.size / 2  # drawing is the minority
    if invert:
        mask = cv2.bitwise_not(mask)
    return mask


def find_curves(mask: np.ndarray, min_length: float = 40.0, holes: bool = False) -> list[np.ndarray]:
    """Trace the outlines in a binary mask.

    Returns a list of complex arrays (x + iy) in pixel coordinates, largest first.
    ``holes=True`` also returns inner outlines (e.g. the inside of an 'O').
    """
    mode = cv2.RETR_LIST if holes else cv2.RETR_EXTERNAL
    contours, _ = cv2.findContours(mask, mode, cv2.CHAIN_APPROX_NONE)
    curves = []
    for c in contours:
        if cv2.arcLength(c, closed=True) < min_length:
            continue
        pts = c[:, 0, :].astype(float)
        curves.append(pts[:, 0] + 1j * pts[:, 1])
    curves.sort(key=lambda z: -np.abs(np.diff(z)).sum())
    return curves


def to_math_coords(curves: list[np.ndarray], width: int, height: int, normalize: bool = True) -> list[np.ndarray]:
    """Flip y so the picture is upright, centre on the image, optionally scale to [-1, 1]."""
    out = []
    scale = max(width, height) / 2 if normalize else 1.0
    for z in curves:
        x = z.real - width / 2
        y = height / 2 - z.imag
        out.append((x + 1j * y) / scale)
    return out


def resample(z: np.ndarray, n: int) -> np.ndarray:
    """Resample a closed curve to ``n`` points evenly spaced by arc length."""
    closed = np.append(z, z[0])
    seg = np.abs(np.diff(closed))
    s = np.concatenate([[0], np.cumsum(seg)])
    targets = np.linspace(0, s[-1], n, endpoint=False)
    re = np.interp(targets, s, closed.real)
    im = np.interp(targets, s, closed.imag)
    return re + 1j * im


def join_curves(curves: list[np.ndarray]) -> np.ndarray:
    """Chain several closed curves into one path (greedy nearest-neighbour order).

    The jumps between curves become part of the drawing, but you get a single
    Fourier series for the whole image.
    """
    if not curves:
        raise ValueError("No curves to join")
    remaining = list(curves)
    path = [remaining.pop(0)]
    while remaining:
        end = path[-1][-1]
        best_i, best_j, best_d = 0, 0, np.inf
        for i, c in enumerate(remaining):
            d = np.abs(c - end)
            j = int(np.argmin(d))
            if d[j] < best_d:
                best_i, best_j, best_d = i, j, d[j]
        c = remaining.pop(best_i)
        path.append(np.roll(c, -best_j))  # start the next curve at its closest point
    return np.concatenate(path)
