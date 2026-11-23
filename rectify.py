"""Крок 1–2: фото телефона → вирівняний «скан» аркуша 2100×2970 (10 px = 1 мм).

TODO (пишу сам):
1. Прочитати HEIC через pillow-heif (pillow_heif.register_heif_opener()), врахувати EXIF-орієнтацію,
   перевести в BGR для OpenCV. Перевірити, що розмір 3024×4032 (як у калібровці), інакше масштабувати K.
2. Перемикач --undistort: cv2.undistort з K, dist з calibration.npz (ключі 'K', 'dist').
3. cv2.aruco.ArucoDetector(DICT_4X4_50).detectMarkers → перевірити, що є всі ID 0–3.
4. Зібрати 16 пар точок: кути з фото (px) ↔ кути з sheet_layout.json (мм × 10).
5. cv2.findHomography(src, dst) (спробувати 0 і RANSAC), вивести reprojection error.
6. cv2.warpPerspective → 2100×2970, зберегти debug/<name>_rectified.jpg.
7. Перевірка: знайти шкалу (y=30 мм, x 55–155) — довжина ≈ 1000 px.
"""
