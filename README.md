# fastener-gauge

Measuring and identifying metric screws from a single phone photo on a sheet with ArUco markers.
Calibrated camera → plane homography → millimetres → nearest standard size.

> Work in progress. Results will appear after the experiments.

## How it works
_TODO: pipeline diagram (undistort → ArUco → homography → segmentation → measurement → standard)._

## Results
_TODO: X/N screws identified correctly, Ø and length error ±Y mm (reference: caliper ±0.2 mm)._

| Experiment | Correct | Ø error, mm | L error, mm |
|---|---|---|---|
| top-down, no undistort | | | |
| top-down, with undistort | | | |
| ~20° | | | |
| ~40° | | | |

## Where it breaks and why
_TODO: stainless steel glare, parallax from head height, sheet flatness._

## What it would look like on a production line
_TODO: fixed camera, backlight, telecentric lens._

## Usage
```bash
pip install -r requirements.txt
python make_sheet.py        # sheet for printing (print at 100%)
python rectify.py ...       # TODO
python measure.py ...       # TODO
python evaluate.py ...      # TODO
```
