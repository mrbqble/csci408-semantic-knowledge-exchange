# Payload size per element

Per camera photo. The caption is UTF-8 text; the segmentation map is lossless WebP; the edge map is WebP (`payloads.py`). 'Photo as JPEG q90' re-encodes the original photo at full resolution, the fairer comparison for the PNG real-world photos.

## CARLA v3, current payload (map 1024x576, edges at full resolution)

504 photos (1920x1080).

| element | mean KB | median KB | min KB | max KB | share of payload |
|---|---|---|---|---|---|
| segmentation map | 5.05 | 4.90 | 2.44 | 9.15 | 9.0% |
| edge map | 51.07 | 49.55 | 24.21 | 96.29 | 90.9% |
| caption | 0.04 | 0.04 | 0.01 | 0.10 | 0.1% |
| payload total | 56.16 | 54.63 | 26.70 | 102.26 | 100% |
| photo as stored | 548.3 | 543.0 | 405.9 | 697.0 | payload = 10.2% of it |
| photo as JPEG q90 | 530.6 | 526.2 | 393.4 | 673.5 | payload = 10.6% of it |

## CARLA v3, working-size payload (map and edges at 896x512)

504 photos (1920x1080).

| element | mean KB | median KB | min KB | max KB | share of payload |
|---|---|---|---|---|---|
| segmentation map | 4.36 | 4.21 | 2.11 | 7.92 | 20.9% |
| edge map | 16.44 | 16.08 | 8.43 | 27.28 | 78.9% |
| caption | 0.04 | 0.04 | 0.01 | 0.10 | 0.2% |
| payload total | 20.83 | 20.58 | 11.37 | 32.93 | 100% |
| photo as stored | 548.3 | 543.0 | 405.9 | 697.0 | payload = 3.8% of it |
| photo as JPEG q90 | 530.6 | 526.2 | 393.4 | 673.5 | payload = 3.9% of it |

## Real-world (61 evaluated cases), current payload

183 photos (1920x1080).

| element | mean KB | median KB | min KB | max KB | share of payload |
|---|---|---|---|---|---|
| segmentation map | 4.03 | 4.16 | 0.52 | 5.42 | 7.9% |
| edge map | 46.62 | 43.28 | 21.67 | 82.32 | 92.0% |
| caption | 0.04 | 0.04 | 0.01 | 0.07 | 0.1% |
| payload total | 50.68 | 46.12 | 25.69 | 86.21 | 100% |
| photo as stored | 2348.1 | 2359.4 | 1749.2 | 2870.4 | payload = 2.2% of it |
| photo as JPEG q90 | 376.1 | 369.7 | 258.8 | 500.6 | payload = 13.5% of it |

## Real-world (61 evaluated cases), working-size payload

183 photos (1920x1080).

| element | mean KB | median KB | min KB | max KB | share of payload |
|---|---|---|---|---|---|
| segmentation map | 3.48 | 3.57 | 0.46 | 4.67 | 21.4% |
| edge map | 12.73 | 12.64 | 8.41 | 17.51 | 78.3% |
| caption | 0.04 | 0.04 | 0.01 | 0.07 | 0.3% |
| payload total | 16.26 | 16.59 | 11.17 | 20.34 | 100% |
| photo as stored | 2348.1 | 2359.4 | 1749.2 | 2870.4 | payload = 0.7% of it |
| photo as JPEG q90 | 376.1 | 369.7 | 258.8 | 500.6 | payload = 4.3% of it |

## Real-world, all 366 core cases, current payload

1098 photos (1920x1080).

| element | mean KB | median KB | min KB | max KB | share of payload |
|---|---|---|---|---|---|
| segmentation map | 4.03 | 4.13 | 0.51 | 7.89 | 7.9% |
| edge map | 46.88 | 42.77 | 21.67 | 84.89 | 92.0% |
| caption | 0.04 | 0.04 | 0.01 | 0.07 | 0.1% |
| payload total | 50.95 | 45.92 | 25.65 | 88.83 | 100% |
| photo as stored | 2350.1 | 2352.8 | 1734.2 | 2915.8 | payload = 2.2% of it |
| photo as JPEG q90 | 376.7 | 369.6 | 240.4 | 505.0 | payload = 13.5% of it |

## CARLA v2, current payload

504 photos (1920x1080).

| element | mean KB | median KB | min KB | max KB | share of payload |
|---|---|---|---|---|---|
| segmentation map | 5.08 | 4.86 | 2.69 | 12.53 | 9.1% |
| edge map | 50.48 | 49.74 | 24.41 | 96.74 | 90.8% |
| caption | 0.04 | 0.04 | 0.01 | 0.09 | 0.1% |
| payload total | 55.60 | 54.43 | 27.69 | 101.27 | 100% |
| photo as stored | 547.8 | 548.0 | 416.7 | 714.5 | payload = 10.1% of it |
| photo as JPEG q90 | 529.8 | 531.0 | 403.2 | 689.8 | payload = 10.5% of it |
