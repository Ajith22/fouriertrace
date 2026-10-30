"""fouriertrace: images with simple curves -> complex Fourier series (epicycles)."""

from .contours import find_curves, join_curves, load_binary, resample, to_math_coords
from .fourier import FourierSeries, Term, fourier_series, reconstruction_error

__all__ = [
    "FourierSeries",
    "Term",
    "find_curves",
    "fourier_series",
    "join_curves",
    "load_binary",
    "reconstruction_error",
    "resample",
    "to_math_coords",
]
__version__ = "0.1.0"
