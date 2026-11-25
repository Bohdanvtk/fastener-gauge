"""Steps 3–5: rectified sheet -> screw contours -> diameter and length in mm -> nearest standard.

Usage:
    python measure.py photos/top.HEIC               # rectify + measure
    python measure.py photos/top.HEIC --undistort

Outputs (in debug/, <stem> = photo name, +"_ud" with --undistort):
    <stem>_mask.png          binary mask of the work zone after Otsu + close
    <stem>_labeled.jpg       work zone with contours and labels "M3x20 (3.05/19.8)"
    <stem>_measurements.csv  one row per detected object (input for evaluate.py)
"""
import argparse
import csv
from pathlib import Path

import cv2
import numpy as np

from rectify import DEBUG_DIR, load_calibration, load_layout, read_image, rectify

MIN_AREA_PX = 200            # drop specks smaller than 2 mm²
CLOSE_KERNEL = 7             # px; fills glare holes on stainless steel
STD_D = (3, 4, 5, 6)
STD_L = (6, 8, 10, 12, 16, 20, 25, 30)
TOL_D = 0.4                  # mm, otherwise "?"
TOL_L = 1.0                  # mm, otherwise "?"
HEAD_RATIO = 1.25            # column is "head" while thickness > HEAD_RATIO * shank median
TIP_SKIP = 0.05              # ignore the last 5 % of length (tip chamfer)
ROW_MM = 30                  # objects whose centres differ by less than this in y share a row


def crop_work_zone(rectified, layout):
    k = layout["px_per_mm"]
    z = layout["crop_zone_mm"]
    x0, y0, x1, y1 = (int(round(v * k)) for v in (z["x0"], z["y0"], z["x1"], z["y1"]))
    return rectified[y0:y1, x0:x1], (x0, y0)


def segment(crop):
    """Otsu (dark screws on white paper) + morphological close -> binary mask 0/255."""
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (CLOSE_KERNEL, CLOSE_KERNEL))
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)


def find_objects(mask):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    return [c for c in contours if cv2.contourArea(c) >= MIN_AREA_PX]


def horizontal_mask(contour):
    """Filled mask of one contour, rotated so its long axis (minAreaRect) is horizontal."""
    rect = cv2.minAreaRect(contour)
    (cx, cy), (w, h), _ = rect
    # direction of the long side, in image coords (y down)
    box = cv2.boxPoints(rect)
    edges = [box[1] - box[0], box[2] - box[1]]
    long_edge = max(edges, key=np.linalg.norm)
    angle = np.degrees(np.arctan2(long_edge[1], long_edge[0]))
    # getRotationMatrix2D(+angle) turns the image counter-clockwise on screen,
    # which brings an edge at +angle (clockwise on screen, y down) to horizontal
    pad = int(max(w, h)) // 2 + 10
    x, y, bw, bh = cv2.boundingRect(contour)
    canvas = np.zeros((bh + 2 * pad, bw + 2 * pad), np.uint8)
    shifted = contour - [x - pad, y - pad]
    cv2.drawContours(canvas, [shifted], -1, 255, cv2.FILLED)
    centre = (cx - x + pad, cy - y + pad)
    M = cv2.getRotationMatrix2D(centre, angle, 1.0)
    rotated = cv2.warpAffine(canvas, M, canvas.shape[::-1], flags=cv2.INTER_NEAREST)
    return rotated, angle


def measure_profile(rotated, px_per_mm):
    """Thickness profile along the axis -> (d_mm, L_mm, profile, head_on_left)."""
    profile = np.count_nonzero(rotated, axis=0)
    cols = np.nonzero(profile)[0]
    profile = profile[cols[0]:cols[-1] + 1].astype(np.float64)
    n = len(profile)
    length_px = n

    # put the head on the left: the head end is the thicker one
    q = max(1, n // 6)
    head_left = profile[:q].mean() >= profile[-q:].mean()
    if not head_left:
        profile = profile[::-1]

    # rough shank thickness from the middle-to-tip part, then skip the head columns
    shank_med = np.median(profile[int(0.4 * n):int(0.9 * n)])
    # head = thick columns in the left half; the shank starts after the last of them
    # (not "first thin column": the very first column after rotation can be a thin sliver)
    thick = np.nonzero(profile[:n // 2] > HEAD_RATIO * shank_med)[0]
    start = thick[-1] + 1 if len(thick) else 0
    end = int(n * (1 - TIP_SKIP))
    shank = profile[start:end]
    if len(shank) < 5:
        shank = profile
    d_px = np.percentile(shank, 95)
    return d_px / px_per_mm, length_px / px_per_mm, profile, start


def nearest(value, standards, tol):
    best = min(standards, key=lambda s: abs(s - value))
    return best if abs(best - value) <= tol else None


def make_label(d_std, l_std):
    d = f"M{d_std}" if d_std is not None else "M?"
    l = str(l_std) if l_std is not None else "?"
    return f"{d}x{l}"


def measure(rectified, layout):
    """Return (list of result dicts, mask, crop, crop offset in px)."""
    k = layout["px_per_mm"]
    crop, (ox, oy) = crop_work_zone(rectified, layout)
    mask = segment(crop)
    results = []
    for c in find_objects(mask):
        rotated, angle = horizontal_mask(c)
        d_mm, l_mm, _, head_px = measure_profile(rotated, k)
        d_std, l_std = nearest(d_mm, STD_D, TOL_D), nearest(l_mm, STD_L, TOL_L)
        (cx, cy), _, _ = cv2.minAreaRect(c)
        results.append({
            "cx_mm": (cx + ox) / k, "cy_mm": (cy + oy) / k, "angle_deg": angle,
            "d_mm": d_mm, "L_mm": l_mm, "head_mm": head_px / k,
            "d_std": d_std, "L_std": l_std, "label": make_label(d_std, l_std),
            "area_mm2": cv2.contourArea(c) / k ** 2, "contour": c,
        })
    # reading order: rows of ROW_MM, then left to right (final row matching is in evaluate.py)
    results.sort(key=lambda r: (round(r["cy_mm"] / ROW_MM), r["cx_mm"]))
    return results, mask, crop, (ox, oy)


def draw_labels(crop, results):
    vis = crop.copy()
    for i, r in enumerate(results):
        c = r["contour"]
        ok = r["d_std"] is not None and r["L_std"] is not None
        colour = (0, 160, 0) if ok else (0, 0, 255)
        cv2.drawContours(vis, [c], -1, colour, 2)
        box = cv2.boxPoints(cv2.minAreaRect(c)).astype(np.int32)
        cv2.polylines(vis, [box], True, (255, 0, 0), 1)
        x, y, w, h = cv2.boundingRect(c)
        text = f"#{i} {r['label']} ({r['d_mm']:.2f}/{r['L_mm']:.1f})"
        org = (x, max(30, y - 12))
        cv2.putText(vis, text, org, cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 5, cv2.LINE_AA)
        cv2.putText(vis, text, org, cv2.FONT_HERSHEY_SIMPLEX, 1.0, colour, 2, cv2.LINE_AA)
    return vis


def save_csv(path, results):
    fields = ["idx", "cx_mm", "cy_mm", "angle_deg", "d_mm", "L_mm", "head_mm",
              "area_mm2", "d_std", "L_std", "label"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i, r in enumerate(results):
            row = {k: r[k] for k in fields if k != "idx"}
            for k in ("cx_mm", "cy_mm", "angle_deg", "d_mm", "L_mm", "head_mm", "area_mm2"):
                row[k] = f"{row[k]:.3f}"
            w.writerow({"idx": i, **row})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", help="photo (HEIC/JPG/PNG)")
    ap.add_argument("--undistort", action="store_true", help="apply cv2.undistort with calibration.npz")
    args = ap.parse_args()

    layout = load_layout()
    img = read_image(args.image)
    K = dist = None
    if args.undistort:
        K, dist = load_calibration((img.shape[1], img.shape[0]))
    rectified, _, info = rectify(img, layout, K, dist)
    print(f"rectified: reprojection error mean {info['reproj_mean']:.2f} px")

    results, mask, crop, _ = measure(rectified, layout)
    print(f"objects: {len(results)}")
    for i, r in enumerate(results):
        print(f"  #{i}: {r['label']:7s} d={r['d_mm']:.2f} mm  L={r['L_mm']:.2f} mm  "
              f"head={r['head_mm']:.1f} mm  at ({r['cx_mm']:.0f}, {r['cy_mm']:.0f}) mm")

    DEBUG_DIR.mkdir(exist_ok=True)
    stem = Path(args.image).stem + ("_ud" if args.undistort else "")
    cv2.imwrite(str(DEBUG_DIR / f"{stem}_mask.png"), mask)
    cv2.imwrite(str(DEBUG_DIR / f"{stem}_labeled.jpg"), draw_labels(crop, results))
    save_csv(DEBUG_DIR / f"{stem}_measurements.csv", results)
    print(f"saved debug/{stem}_mask.png, _labeled.jpg, _measurements.csv")


if __name__ == "__main__":
    main()
