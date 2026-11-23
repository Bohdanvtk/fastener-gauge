"""Step 6: compare measurements with ground_truth.csv (caliper).

TODO (written by me):
1. Screws are laid out in rows -> sort detections (row by y, then x) and assign ids.
2. Match with ground_truth.csv (id,nominal,d_caliper_mm,L_caliper_mm).
3. Metrics: share of correct labels (X/N), Ø and L error in mm (mean, max, std).
4. Table for README; run for each experiment (with/without undistort, angles 0°/20°/40°).
"""
