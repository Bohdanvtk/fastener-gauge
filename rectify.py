"""Steps 1–2: phone photo -> rectified "scan" of the sheet, 2100x2970 (10 px = 1 mm).

Usage:
    python rectify.py photos/top.HEIC                # without undistort
    python rectify.py photos/top.HEIC --undistort    # with cv2.undistort (K, dist)
    python rectify.py sheet_preview.png              # sanity check on the generated sheet

Outputs debug/<name>[_ud]_markers.jpg and debug/<name>[_ud]_rectified.jpg.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent
LAYOUT_PATH = ROOT / "sheet_layout.json"
CALIB_PATH = ROOT / "calibration.npz"
DEBUG_DIR = ROOT / "debug"

CALIB_SIZE = (3024, 4032)  # (w, h) of the calibration images
EXPECTED_IDS = (0, 1, 2, 3)


def load_layout(path=LAYOUT_PATH):
    with open(path) as f:
        return json.load(f)


def read_image(path):
    """Read HEIC/JPG/PNG, apply EXIF orientation, return BGR uint8."""
    path = Path(path)
    if path.suffix.lower() in (".heic", ".heif"):
        import pillow_heif
        pillow_heif.register_heif_opener()
    img = Image.open(path)
    img = ImageOps.exif_transpose(img).convert("RGB")
    return cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)


def load_calibration(img_size, path=CALIB_PATH):
    """Return K, dist; scale K if the image size differs from the calibration size."""
    data = np.load(path)
    K, dist = data["K"].astype(np.float64), data["dist"].astype(np.float64)
    w, h = img_size
    cw, ch = CALIB_SIZE
    if (w, h) != (cw, ch):
        if (w, h) == (ch, cw):
            raise ValueError(f"Image is {w}x{h} (rotated vs calibration {cw}x{ch}); "
                             "K would need its axes swapped — shoot in portrait.")
        sx, sy = w / cw, h / ch
        print(f"[warn] image {w}x{h} != calibration {cw}x{ch}, scaling K by ({sx:.3f}, {sy:.3f})")
        K = K.copy()
        K[0, :] *= sx
        K[1, :] *= sy
    return K, dist


def detect_markers(gray, dict_name):
    dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, dict_name))
    params = cv2.aruco.DetectorParameters()
    params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    detector = cv2.aruco.ArucoDetector(dictionary, params)
    corners, ids, _ = detector.detectMarkers(gray)
    found = {}
    if ids is not None:
        for c, i in zip(corners, ids.ravel()):
            found[int(i)] = c.reshape(4, 2)
    return found, corners, ids


def build_point_pairs(found, layout):
    """16 pairs: marker corners in the photo (px) <-> layout corners (mm * px_per_mm)."""
    k = layout["px_per_mm"]
    src, dst = [], []
    for mid in EXPECTED_IDS:
        src.append(found[mid])
        dst.append(np.asarray(layout["markers"][str(mid)], np.float64) * k)
    return np.vstack(src).astype(np.float64), np.vstack(dst).astype(np.float64)


def reprojection_error(H, src, dst):
    proj = cv2.perspectiveTransform(src.reshape(-1, 1, 2), H).reshape(-1, 2)
    err = np.linalg.norm(proj - dst, axis=1)
    return err.mean(), err.max()


def measure_scale(rectified, layout):
    """Distance in px between the long ticks at 0 and 100 mm of the printed scale.

    Long ticks (0/50/100 mm) are 60 px high above the line; a band 45–55 px above the
    line crosses only them. Expected result ≈ 1000 px.
    """
    k = layout["px_per_mm"]
    s = layout["scale_line_mm"]
    y = int(round(s["y"] * k))
    x0, x1 = int((s["x0"] - 5) * k), int((s["x1"] + 5) * k)
    gray = cv2.cvtColor(rectified, cv2.COLOR_BGR2GRAY)
    band = gray[y - 55:y - 45, x0:x1].astype(np.float64).mean(axis=0)
    thr = (band.max() + band.min()) / 2
    dark = band < thr
    # group consecutive dark columns into ticks, take sub-pixel centres
    centres, start = [], None
    for x, d in enumerate(np.append(dark, False)):
        if d and start is None:
            start = x
        elif not d and start is not None:
            w = 255 - band[start:x]
            centres.append(x0 + start + (w * np.arange(len(w))).sum() / w.sum())
            start = None
    if len(centres) < 2:
        return None, centres
    return centres[-1] - centres[0], centres


def rectify(img, layout, K=None, dist=None, method=0):
    """Return (rectified image, H, info dict). Raises if a marker is missing."""
    if K is not None:
        img = cv2.undistort(img, K, dist)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    found, corners, ids = detect_markers(gray, layout["aruco_dict"])
    missing = [i for i in EXPECTED_IDS if i not in found]
    if missing:
        raise RuntimeError(f"Markers not found: {missing} (found {sorted(found)})")

    src, dst = build_point_pairs(found, layout)
    H, _ = cv2.findHomography(src, dst, method, 3.0)
    if H is None:
        raise RuntimeError("findHomography failed")
    mean_err, max_err = reprojection_error(H, src, dst)

    k = layout["px_per_mm"]
    out_size = (layout["page_mm"][0] * k, layout["page_mm"][1] * k)  # (2100, 2970)
    rectified = cv2.warpPerspective(img, H, out_size, flags=cv2.INTER_CUBIC,
                                    borderValue=(255, 255, 255))

    vis = img.copy()
    cv2.aruco.drawDetectedMarkers(vis, corners, ids)
    info = {"found": sorted(found), "reproj_mean": mean_err, "reproj_max": max_err,
            "markers_vis": vis}
    return rectified, H, info


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", help="photo (HEIC/JPG/PNG)")
    ap.add_argument("--undistort", action="store_true", help="apply cv2.undistort with calibration.npz")
    ap.add_argument("--ransac", action="store_true", help="use RANSAC in findHomography (default: all points)")
    args = ap.parse_args()

    layout = load_layout()
    img = read_image(args.image)
    h, w = img.shape[:2]
    print(f"image: {args.image}  {w}x{h}")

    K = dist = None
    if args.undistort:
        K, dist = load_calibration((w, h))

    method = cv2.RANSAC if args.ransac else 0
    rectified, H, info = rectify(img, layout, K, dist, method)
    print(f"markers found: {info['found']}")
    print(f"reprojection error: mean {info['reproj_mean']:.2f} px, max {info['reproj_max']:.2f} px "
          f"(output px, 1 px = 0.1 mm)")

    length, ticks = measure_scale(rectified, layout)
    if length is None:
        print(f"[warn] scale ticks not found (got {len(ticks)})")
    else:
        print(f"scale 0–100 mm: {length:.1f} px (expected 1000) -> {length / 10:.2f} mm")

    DEBUG_DIR.mkdir(exist_ok=True)
    stem = Path(args.image).stem + ("_ud" if args.undistort else "")
    cv2.imwrite(str(DEBUG_DIR / f"{stem}_markers.jpg"), info["markers_vis"])
    cv2.imwrite(str(DEBUG_DIR / f"{stem}_rectified.jpg"), rectified)
    print(f"saved debug/{stem}_markers.jpg, debug/{stem}_rectified.jpg")


if __name__ == "__main__":
    main()
