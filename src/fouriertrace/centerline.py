"""Centerline tracing: follow the middle of a drawn line, straight through crossings.

Outline tracing (contours.find_curves) follows the *edge* of the ink, so a line
that crosses itself (a figure-8, a kolam) only gives its outer boundary.
Here we instead:

1. thin the ink to a 1-pixel skeleton,
2. merge the messy skeleton pixels around each crossing into one "node",
3. split the rest into segments that run between nodes,
4. walk the segments like a pen: at every node, carry on in the direction
   closest to straight ahead.

The result is one closed path per pen stroke, ready for the Fourier series.
"""

from __future__ import annotations

import cv2
import numpy as np
from skimage.morphology import skeletonize

_NEIGH = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]  # 4-neighbours first


def _neighbour_count(img: np.ndarray) -> np.ndarray:
    k = np.ones((3, 3), np.float32)
    k[1, 1] = 0
    return cv2.filter2D(img.astype(np.float32), -1, k, borderType=cv2.BORDER_CONSTANT).astype(int) * img


def _walk(seg: np.ndarray, start: tuple[int, int]) -> np.ndarray:
    """Order the pixels of a thin segment by walking from ``start``."""
    h, w = seg.shape
    visited = {start}
    path = [start]
    y, x = start
    while True:
        for dy, dx in _NEIGH:
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and seg[ny, nx] and (ny, nx) not in visited:
                visited.add((ny, nx))
                path.append((ny, nx))
                y, x = ny, nx
                break
        else:
            break
    p = np.array(path, float)
    return p[:, 1] + 1j * p[:, 0]  # x + iy


def _stroke_width(mask: np.ndarray, skel: np.ndarray) -> float:
    dist = cv2.distanceTransform((mask > 0).astype(np.uint8), cv2.DIST_L2, 5)
    vals = dist[skel > 0]
    return float(2 * np.median(vals)) if vals.size else 2.0


def trace_centerlines(mask: np.ndarray, min_length: float = 40.0) -> list[np.ndarray]:
    """Return closed pen paths (complex x + iy, pixel coords) through a line drawing.

    ``mask`` is a binary image with the ink white. Open strokes are traced out and
    back, so every path is closed. Paths shorter than ``min_length`` are dropped.
    """
    ink = mask > 0
    skel = skeletonize(ink).astype(np.uint8)
    width = _stroke_width(mask, skel)

    # 1. junction pixels -> merged node blobs (one per crossing)
    nc = _neighbour_count(skel)
    junctions = ((nc >= 3) & (skel > 0)).astype(np.uint8)
    r = max(2, int(round(width)))
    disk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    node_area = cv2.dilate(junctions, disk) & ink.astype(np.uint8)
    n_nodes, node_lbl = cv2.connectedComponents(node_area, connectivity=8)
    node_centre = {}
    for k in range(1, n_nodes):
        ys, xs = np.nonzero((node_lbl == k) & (skel > 0))
        if ys.size == 0:
            ys, xs = np.nonzero(node_lbl == k)
        node_centre[k] = xs.mean() + 1j * ys.mean()

    # 2. what's left of the skeleton splits into segments between nodes
    rest = skel.copy()
    rest[node_area > 0] = 0
    n_seg, seg_lbl = cv2.connectedComponents(rest, connectivity=8)
    seg_nc = _neighbour_count(rest)
    h, w = rest.shape

    def touching_node(z: complex) -> int | None:
        x, y = int(round(z.real)), int(round(z.imag))
        win = node_lbl[max(0, y - 2): y + 3, max(0, x - 2): x + 3]
        ids = win[win > 0]
        return int(np.bincount(ids).argmax()) if ids.size else None

    edges = []      # dicts: pts, a (node at start or None), b (node at end or None)
    loops = []      # closed segments that touch no node (simple loops)
    for k in range(1, n_seg):
        seg = seg_lbl == k
        ys, xs = np.nonzero(seg)
        ends = [(y, x) for y, x in zip(ys, xs) if seg_nc[y, x] <= 1]
        if not ends:  # a ring with no crossings
            pts = _walk(seg, (int(ys[0]), int(xs[0])))
            if len(pts) > 2 and np.abs(np.diff(pts)).sum() >= min_length:
                loops.append(pts)
            continue
        pts = _walk(seg, ends[0])
        edges.append({"pts": pts, "a": touching_node(pts[0]), "b": touching_node(pts[-1])})

    # 3. tidy: drop specks and short spurs that dead-end next to a node
    def length(e):
        return float(np.abs(np.diff(e["pts"])).sum()) if len(e["pts"]) > 1 else 0.0

    kept = []
    for e in edges:
        free = (e["a"] is None) + (e["b"] is None)
        if free == 2 and length(e) < min_length:
            continue  # isolated speck (e.g. a dot)
        if free == 1 and length(e) < 2.5 * width:
            continue  # skeleton spur
        kept.append(e)
    edges = kept

    # 4. walk like a pen
    look = max(4, int(round(1.5 * width)))

    def out_dir(e, at_start: bool) -> complex:
        p = e["pts"] if at_start else e["pts"][::-1]
        d = p[min(len(p) - 1, look)] - p[0]
        return d / abs(d) if abs(d) else 0j

    incident: dict[int, list[tuple[int, bool]]] = {}
    for i, e in enumerate(edges):
        if e["a"] is not None:
            incident.setdefault(e["a"], []).append((i, True))
        if e["b"] is not None:
            incident.setdefault(e["b"], []).append((i, False))

    used = [False] * len(edges)
    paths = []
    order = sorted(range(len(edges)), key=lambda i: -length(edges[i]))
    for first in order:
        if used[first]:
            continue
        path = []
        i, forward = first, True
        for _ in range(4 * len(edges) + 4):
            e = edges[i]
            used[i] = True
            pts = e["pts"] if forward else e["pts"][::-1]
            path.append(pts)
            node = e["b"] if forward else e["a"]
            if node is None:  # pen reaches a loose end: come back along the same line
                back = pts[::-1]
                path.append(back)
                node = e["a"] if forward else e["b"]
                if node is None:
                    break
                arrive = -out_dir(e, at_start=forward)  # arriving back at the far node
                came_from = (i, forward)
            else:
                arrive = -out_dir(e, at_start=not forward)
                came_from = (i, not forward)
            if node in node_centre:
                path.append(np.array([node_centre[node]]))
            best, best_score = None, -np.inf
            for j, at_start in incident.get(node, []):
                if (j, at_start) == came_from:
                    continue
                score = np.real(np.conj(arrive) * out_dir(edges[j], at_start))  # cos(angle)
                if score > best_score:
                    best, best_score = (j, at_start), score
            if best is None or used[best[0]]:
                break
            i, forward = best
        z = np.concatenate(path)
        if len(z) > 2 and np.abs(np.diff(z)).sum() >= min_length:
            paths.append(z)

    paths += loops
    paths.sort(key=lambda z: -np.abs(np.diff(z)).sum())
    return paths
