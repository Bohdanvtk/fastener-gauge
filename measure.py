"""Steps 3–5: rectified sheet -> screw contours -> diameter and length in mm -> nearest standard.

TODO (written by me):
1. Crop to crop_zone_mm from sheet_layout.json (x 13–197, y 63–234 mm -> ×10 px).
2. Grayscale -> cv2.threshold(BINARY_INV + OTSU) -> MORPH_CLOSE (fill glare / slot).
3. cv2.findContours(RETR_EXTERNAL), drop area < 200 px².
4. For each contour: minAreaRect -> rotate the mask so the screw axis is horizontal.
5. Thickness profile: count_nonzero per column.
   Ø = 95th percentile of SHANK thickness (without head) / 10; length = full length / 10
   (for countersunk screws the length includes the head).
6. Nearest standard: Ø ∈ {3,4,5,6} ("?" if |Δ| > 0.4), L ∈ {6,8,10,12,16,20,25,30} ("?" if |Δ| > 1).
7. Draw labels "M3×20 (3.05/19.8)" -> debug/labeled.jpg.
"""
