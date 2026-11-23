# fastener-gauge

Portfolio project: measuring and identifying metric screws from ONE phone photo on a printed
sheet with ArUco markers. Prototype of industrial inspection: calibrated camera → plane → mm →
nearest standard size.

## Working rules (important)
- The core logic (`rectify.py`, `measure.py`, `evaluate.py`) is written by the user THEMSELVES.
  Claude: structure, explanations, review, help with errors. Do not write these files for the user unless asked.
- Everything in the repo (code, comments, docstrings, README, commit messages) is in English.
- Chat replies: in Ukrainian, short, main point first.
- Do not expand the project: no neural networks, scope ~1 week.
- Python: `.venv/bin/python` (Python 3.10).

## Files
- `make_sheet.py` → `sheet.pdf` (254 DPI), `sheet_preview.png`, `sheet_layout.json`. The sheet is ALREADY printed —
  do not change the geometry.
- `sheet_layout.json` — marker corners in mm in detectMarkers order (TL, TR, BR, BL), `crop_zone_mm`, scale.
- `calibration.npz` — keys `K`, `dist` (copied from `~/PycharmProjects/Computer_vision_calibration`).
- `photos/` — original HEIC files (committed), `debug/` — intermediate images (ignored).
- `ground_truth.csv` — `id,nominal,d_caliper_mm,L_caliper_mm`.

## Sheet (A4, 10 px = 1 mm → 2100×2970)
- ArUco `DICT_4X4_50`, IDs 0–3, side 40 mm. Top-left corner (mm): 0:(10,10) 1:(160,10) 2:(10,247) 3:(160,247).
- 100 mm scale: y=30 mm, x 55→155, with ticks.
- Work zone (dashed): x 10–200, y 60–237 mm. Crop with 3 mm inset: x 13–197, y 63–234.
- Printed at 100% (actual size), the 100 mm line was checked with the caliper — ok
  (exact value: _to be filled in by the user_).

## Camera
- iPhone 14, photos are original HEIC (read with `pillow-heif`).
- Calibration from a previous project: K ≈ [[3032.8,0,1501.4],[0,3051.6,2009.5],[0,0,1]], size 3024×4032,
  dist (k1,k2,p1,p2,k3) ≈ [0.245, -1.267, 0, 0, 2.099], RMS 1.45 px.
- Weakness: the board was only in the centre of the frame → distortion is unreliable at the edges.
  Hypothesis: the iPhone already corrects distortion itself, and the k-coefficients are overfitting.
  Tested by the "with and without undistort" experiment.

## Parts and reference
- Stainless steel A2, countersunk head (Senkkopf) with slot, 8 pcs each: M3×10, M3×20, M4×20. No nuts.
- Countersunk screw length INCLUDES the head.
- Check pairs: M3×10 vs M3×20 (length), M3×20 vs M4×20 (diameter).
- Reference: analog caliper 150 mm, vernier 0.1 mm, accuracy ±0.2 mm.
  Extra: coins 1€ = 23.25, 2€ = 25.75, 50c = 24.25 mm.

## Pipeline
1. undistort (on/off switch).
2. ArUco → 16 point pairs (px ↔ mm×10) → `findHomography` → `warpPerspective` 2100×2970.
   Check: scale ≈ 1000 px.
3. Crop to work zone, Otsu (`BINARY_INV+OTSU`), `MORPH_CLOSE`, `findContours` EXTERNAL, drop < 200 px².
4. `minAreaRect`, rotate mask horizontal, thickness profile `count_nonzero` per column;
   Ø = 95th percentile of shank thickness / 10, length = full / 10.
5. Nearest standard: Ø {3,4,5,6} ("?" if |Δ|>0.4), length {6,8,10,12,16,20,25,30} ("?" if |Δ|>1)
   → `debug/labeled.jpg`.
6. evaluate: screws in rows, match with `ground_truth.csv`, label accuracy + Ø and length error in mm.

## Experiments for README
- With/without undistort.
- Shooting angle: top-down / ~20° / ~40°.
- Limits: stainless steel glare, head height (parallax), sheet flatness.

## README goal
"Calibrated the camera → built a homography-based measurement station → verified with a caliper:
X/N screws correct, ±Y mm. Here is where it breaks and why. On a production line: fixed camera, backlight,
telecentric lens."

## Status
- [x] Sheet printed, screws and caliper bought.
- [x] Repo structure, `make_sheet.py` (detection of IDs 0–3 on the generated sheet verified).
- [x] Public GitHub repo: https://github.com/Bohdanvtk/fastener-gauge
- [ ] 3 photos (top-down, ~20°, ~40°) with 3 screws, all 4 markers in frame, diffuse light.
- [ ] `rectify.py` — done when: IDs 0–3 found, top.jpg looks like a scan, scale ≈ 1000 px.
- [ ] `measure.py`
- [ ] Caliper measurements → `ground_truth.csv`, `evaluate.py`
- [ ] README with experiment results.
