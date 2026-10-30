"""Preview images and epicycle animations."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FFMpegWriter, FuncAnimation, PillowWriter

from .fourier import FourierSeries

BG = "#0f1117"
INK = "#f4d35e"
CIRCLE = "#5c6b8a"
ARM = "#c3cfe2"
FAINT = "#3a4256"


def _bounds(curves: list[np.ndarray], pad: float = 0.08):
    allz = np.concatenate(curves)
    xmin, xmax = allz.real.min(), allz.real.max()
    ymin, ymax = allz.imag.min(), allz.imag.max()
    span = max(xmax - xmin, ymax - ymin) * (1 + 2 * pad)
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
    return (cx - span / 2, cx + span / 2), (cy - span / 2, cy + span / 2)


def _axes(figsize=6):
    fig, ax = plt.subplots(figsize=(figsize, figsize), facecolor=BG)
    ax.set_facecolor(BG)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.subplots_adjust(0, 0, 1, 1)
    return fig, ax


def save_preview(originals: list[np.ndarray], series_list: list[FourierSeries], path: str, samples: int = 2000) -> None:
    """Original outline (faint) under the reconstructed series (bright)."""
    t = np.linspace(0, 2 * np.pi, samples)
    recon = [s(t) for s in series_list]
    fig, ax = _axes()
    for z in originals:
        zc = np.append(z, z[0])
        ax.plot(zc.real, zc.imag, color=FAINT, lw=4)
    for z in recon:
        ax.plot(z.real, z.imag, color=INK, lw=1.4)
    xl, yl = _bounds(originals + recon)
    ax.set_xlim(xl)
    ax.set_ylim(yl)
    fig.savefig(path, dpi=150, facecolor=BG)
    plt.close(fig)


def save_animation(
    series_list: list[FourierSeries],
    path: str,
    frames: int = 240,
    fps: int = 30,
    max_circles: int = 60,
) -> None:
    """Epicycle animation: each curve gets its own chain of spinning circles.

    Writes a GIF, or an MP4 if the path ends in .mp4 (needs ffmpeg).
    """
    ts = np.linspace(0, 2 * np.pi, frames, endpoint=False)
    full = [s(np.linspace(0, 2 * np.pi, 1000)) for s in series_list]
    fig, ax = _axes()
    xl, yl = _bounds(full)
    ax.set_xlim(xl)
    ax.set_ylim(yl)

    chains = []
    for s in series_list:
        terms = s.sorted_for_drawing()
        const = sum((t.c for t in terms if t.n == 0), 0j)
        moving = [t for t in terms if t.n != 0]
        shown, rest = moving[:max_circles], moving[max_circles:]
        circles = [
            ax.add_patch(plt.Circle((0, 0), t.radius, fill=False, color=CIRCLE, lw=0.6, alpha=0.7))
            for t in shown
        ]
        (arm,) = ax.plot([], [], color=ARM, lw=0.8)
        (trace,) = ax.plot([], [], color=INK, lw=1.6)
        (tip,) = ax.plot([], [], "o", color=INK, ms=3)
        chains.append(dict(const=const, shown=shown, rest=FourierSeries(rest), circles=circles,
                           arm=arm, trace=trace, tip=tip, path=[]))

    def update(frame):
        t = ts[frame]
        artists = []
        for ch in chains:
            pos = ch["const"]
            joints = [pos]
            for term, circ in zip(ch["shown"], ch["circles"]):
                circ.center = (pos.real, pos.imag)
                pos = pos + term.c * np.exp(1j * term.n * t)
                joints.append(pos)
            if ch["rest"].terms:
                pos = pos + complex(ch["rest"](t))  # small terms: no circles, still drawn
                joints.append(pos)
            ch["path"].append(pos)
            j = np.array(joints)
            p = np.array(ch["path"])
            ch["arm"].set_data(j.real, j.imag)
            ch["trace"].set_data(p.real, p.imag)
            ch["tip"].set_data([pos.real], [pos.imag])
            artists += ch["circles"] + [ch["arm"], ch["trace"], ch["tip"]]
        return artists

    anim = FuncAnimation(fig, update, frames=frames, blit=True, interval=1000 / fps)
    writer = FFMpegWriter(fps=fps) if path.lower().endswith(".mp4") else PillowWriter(fps=fps)
    anim.save(path, writer=writer, dpi=100, savefig_kwargs={"facecolor": BG})
    plt.close(fig)
