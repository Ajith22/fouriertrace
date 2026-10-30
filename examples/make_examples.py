"""Generate sample input images: python examples/make_examples.py"""

import os

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def heart_and_star(path):
    img = np.full((500, 800), 255, np.uint8)  # black shapes on white
    t = np.linspace(0, 2 * np.pi, 400)
    x = 16 * np.sin(t) ** 3
    y = 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)
    heart = np.stack([220 + 11 * x, 240 - 11 * y], axis=1).astype(np.int32)
    cv2.fillPoly(img, [heart], 0)

    angles = np.pi / 2 + np.arange(10) * np.pi / 5
    radii = np.where(np.arange(10) % 2 == 0, 190, 80)
    star = np.stack([580 + radii * np.cos(angles), 250 - radii * np.sin(angles)], axis=1).astype(np.int32)
    cv2.fillPoly(img, [star], 0)
    cv2.imwrite(path, img)


def line_drawing(path):
    img = np.full((500, 500), 255, np.uint8)  # thin strokes: outline of a stroke is traced
    t = np.linspace(0, 2 * np.pi, 600)
    r = 170 + 40 * np.sin(5 * t)
    pts = np.stack([250 + r * np.cos(t), 250 + r * np.sin(t)], axis=1).astype(np.int32)
    cv2.polylines(img, [pts], True, 0, 6, cv2.LINE_AA)
    cv2.imwrite(path, img)


if __name__ == "__main__":
    heart_and_star(os.path.join(HERE, "heart_star.png"))
    line_drawing(os.path.join(HERE, "flower_line.png"))
    print("wrote examples/heart_star.png and examples/flower_line.png")
