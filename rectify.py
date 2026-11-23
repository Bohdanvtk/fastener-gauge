"""Steps 1–2: phone photo -> rectified "scan" of the sheet, 2100x2970 (10 px = 1 mm).

TODO (written by me):
1. Read HEIC via pillow-heif (pillow_heif.register_heif_opener()), apply EXIF orientation,
   convert to BGR for OpenCV. Check the size is 3024x4032 (as in calibration), otherwise scale K.
2. --undistort switch: cv2.undistort with K, dist from calibration.npz (keys 'K', 'dist').
3. cv2.aruco.ArucoDetector(DICT_4X4_50).detectMarkers -> check that all IDs 0–3 are found.
4. Build 16 point pairs: corners in the photo (px) <-> corners from sheet_layout.json (mm × 10).
5. cv2.findHomography(src, dst) (try 0 and RANSAC), print reprojection error.
6. cv2.warpPerspective -> 2100x2970, save debug/<name>_rectified.jpg.
7. Check: find the scale (y=30 mm, x 55–155) — length ≈ 1000 px.
"""
