"""Complex Fourier series of a closed curve.

A closed curve z(t), t in [0, 2*pi), is written as

    z(t) = sum_n  c_n * exp(i * n * t)

Each term is a circle (an "epicycle") of radius |c_n|, starting angle arg(c_n),
spinning n times per loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class Term:
    n: int          # frequency (turns per loop; negative = clockwise)
    c: complex      # coefficient

    @property
    def radius(self) -> float:
        return abs(self.c)

    @property
    def phase(self) -> float:
        return float(np.angle(self.c))


@dataclass
class FourierSeries:
    terms: list[Term] = field(default_factory=list)

    def __call__(self, t: np.ndarray | float) -> np.ndarray:
        t = np.asarray(t, dtype=float)
        z = np.zeros_like(t, dtype=complex)
        for term in self.terms:
            z = z + term.c * np.exp(1j * term.n * t)
        return z

    def truncate(self, k: int) -> "FourierSeries":
        """Keep the constant term plus the k largest other terms (by radius)."""
        const = [t for t in self.terms if t.n == 0]
        rest = sorted((t for t in self.terms if t.n != 0), key=lambda t: -t.radius)
        return FourierSeries(const + rest[:k])

    def sorted_for_drawing(self) -> list[Term]:
        """Constant term first, then biggest circles first (nicest epicycle chain)."""
        const = [t for t in self.terms if t.n == 0]
        rest = sorted((t for t in self.terms if t.n != 0), key=lambda t: -t.radius)
        return const + rest


def fourier_series(z: np.ndarray, terms: int | None = None) -> FourierSeries:
    """Compute the Fourier series of evenly sampled closed-curve points ``z``.

    ``terms`` keeps only the largest N non-constant terms; None keeps all.
    """
    n_pts = len(z)
    coeffs = np.fft.fft(z) / n_pts
    freqs = np.fft.fftfreq(n_pts, d=1.0 / n_pts).astype(int)
    series = FourierSeries([Term(int(n), complex(c)) for n, c in zip(freqs, coeffs)])
    return series.truncate(terms) if terms is not None else series


def reconstruction_error(series: FourierSeries, z: np.ndarray) -> float:
    """Mean distance between the original samples and the series at the same t."""
    t = 2 * np.pi * np.arange(len(z)) / len(z)
    return float(np.mean(np.abs(series(t) - z)))
