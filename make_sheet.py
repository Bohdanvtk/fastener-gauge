"""Генерує вимірювальний аркуш A4 з ArUco-маркерами.

Масштаб малювання: 10 px = 1 мм → 2100×2970 px.
Виходи: sheet.pdf (254 DPI → точно 210×297 мм), sheet_preview.png, sheet_layout.json.

УВАГА: аркуш уже надруковано. Не змінюй геометрію (маркери, шкала, зона),
інакше sheet_layout.json перестане відповідати паперу.
"""
import json

import cv2
import numpy as np
from PIL import Image

PX_PER_MM = 10
W_MM, H_MM = 210, 297
DPI = 254  # 254 DPI = 10 px/мм

ARUCO_DICT = cv2.aruco.DICT_4X4_50
MARKER_MM = 40
MARKERS_TL_MM = {0: (10, 10), 1: (160, 10), 2: (10, 247), 3: (160, 247)}

SCALE_Y_MM = 30
SCALE_X0_MM, SCALE_X1_MM = 55, 155  # 100 мм

ZONE_MM = (10, 60, 200, 237)  # x0, y0, x1, y1 — пунктирна робоча зона
CROP_INSET_MM = 3


def mm(v):
    return int(round(v * PX_PER_MM))


def draw_dashed_rect(img, x0, y0, x1, y1, dash=60, gap=40, thickness=3):
    def dashed_line(p, q):
        p, q = np.array(p, float), np.array(q, float)
        length = np.linalg.norm(q - p)
        direction = (q - p) / length
        s = 0.0
        while s < length:
            e = min(s + dash, length)
            a = tuple(np.round(p + direction * s).astype(int))
            b = tuple(np.round(p + direction * e).astype(int))
            cv2.line(img, a, b, 0, thickness)
            s += dash + gap

    dashed_line((x0, y0), (x1, y0))
    dashed_line((x1, y0), (x1, y1))
    dashed_line((x1, y1), (x0, y1))
    dashed_line((x0, y1), (x0, y0))


def build_sheet():
    img = np.full((mm(H_MM), mm(W_MM)), 255, np.uint8)
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)

    # Маркери
    side = mm(MARKER_MM)
    for mid, (x, y) in MARKERS_TL_MM.items():
        marker = cv2.aruco.generateImageMarker(aruco_dict, mid, side)
        img[mm(y):mm(y) + side, mm(x):mm(x) + side] = marker

    # Шкала 100 мм із засічками кожні 10 мм (довші на 0/50/100) і дрібні кожні 1 мм
    y = mm(SCALE_Y_MM)
    x0, x1 = mm(SCALE_X0_MM), mm(SCALE_X1_MM)
    cv2.line(img, (x0, y), (x1, y), 0, 3)
    for i in range(0, 101):
        x = x0 + i * PX_PER_MM
        if i % 50 == 0:
            h = 60
        elif i % 10 == 0:
            h = 40
        elif i % 5 == 0:
            h = 25
        else:
            h = 15
        cv2.line(img, (x, y - h), (x, y), 0, 3 if i % 10 == 0 else 1)
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, "0", (x0 - 12, y + 45), font, 1.0, 0, 2, cv2.LINE_AA)
    cv2.putText(img, "100 mm", (x1 - 50, y + 45), font, 1.0, 0, 2, cv2.LINE_AA)
    cv2.putText(img, "fastener-gauge | A4 | print at 100%", (x0 + 120, y + 130),
                font, 0.9, 0, 2, cv2.LINE_AA)

    # Робоча зона
    zx0, zy0, zx1, zy1 = (mm(v) for v in ZONE_MM)
    draw_dashed_rect(img, zx0, zy0, zx1, zy1)
    return img


def build_layout():
    markers = {}
    for mid, (x, y) in MARKERS_TL_MM.items():
        s = MARKER_MM
        # порядок кутів як у cv2.aruco detectMarkers: TL, TR, BR, BL
        markers[str(mid)] = [[x, y], [x + s, y], [x + s, y + s], [x, y + s]]
    zx0, zy0, zx1, zy1 = ZONE_MM
    i = CROP_INSET_MM
    return {
        "units": "mm",
        "page_mm": [W_MM, H_MM],
        "px_per_mm": PX_PER_MM,
        "aruco_dict": "DICT_4X4_50",
        "marker_size_mm": MARKER_MM,
        "marker_corners_order": "TL,TR,BR,BL (cv2.aruco detectMarkers)",
        "markers": markers,
        "work_zone_mm": {"x0": zx0, "y0": zy0, "x1": zx1, "y1": zy1},
        "crop_zone_mm": {"x0": zx0 + i, "y0": zy0 + i, "x1": zx1 - i, "y1": zy1 - i},
        "scale_line_mm": {"y": SCALE_Y_MM, "x0": SCALE_X0_MM, "x1": SCALE_X1_MM,
                          "length": SCALE_X1_MM - SCALE_X0_MM},
    }


def main():
    img = build_sheet()
    pil = Image.fromarray(img)
    pil.save("sheet.pdf", resolution=DPI)
    pil.save("sheet_preview.png", dpi=(DPI, DPI))
    with open("sheet_layout.json", "w") as f:
        json.dump(build_layout(), f, indent=2)
    print("saved sheet.pdf, sheet_preview.png, sheet_layout.json")


if __name__ == "__main__":
    main()
