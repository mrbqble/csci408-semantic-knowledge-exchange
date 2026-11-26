# Tuning of Damir's fusion (strength, IP-Adapter scale)

Selection rule fixed in advance: the winner is the setting with the most joint successes on the tuning half (CARLA 1-56 plus the first 30
real-world cases). The current setting (strength 0.5, IP scale 1.0) is replaced only if beaten. The winner is then reported on the held-out half only.

## Tuning half

| Setting | strength | IP scale | CARLA joint | Real-world joint | Total |
|---|---|---|---|---|---|
| st0.5_ip1.0 | 0.5 | 1.0 | 36/56 | 25/29 | 61 |
| st0.3 | 0.3 | 1.0 | 31/56 | 25/29 | 56 |
| st0.4 | 0.4 | 1.0 | 36/56 | 26/29 | 62 |
| st0.6 | 0.6 | 1.0 | 35/56 | 26/29 | 61 |
| ip0.5 | 0.5 | 0.5 | 31/56 | 27/29 | 58 |
| ip0.75 | 0.5 | 0.75 | 34/56 | 27/29 | 61 |

Common judged cases: CARLA 56/56, real-world 29/30. **Winner: st0.4**.

## Held-out half

| Comparison (joint score, McNemar) | CARLA 57-112 | Real-world, last 31 |
|---|---|---|
| joint success | winner 58.9%, current 55.4%, 896x512-support fusion 69.6%, single camera 58.9% (n = 56) | winner 67.7%, current 83.9%, 896x512-support fusion 71.0%, single camera 61.3% (n = 31) |
| winner vs current setting | +3.6 pts (8/6, p = 0.791) | -16.1 pts (1/6, p = 0.125) |
| winner vs single-camera MMSD | +0.0 pts (10/10, p = 1.000) | +6.5 pts (4/2, p = 0.688) |
| current setting vs single-camera MMSD | -3.6 pts (11/13, p = 0.839) | +22.6 pts (7/0, p = 0.016) |
| winner vs fusion with 896x512 supports | -10.7 pts (7/13, p = 0.263) | -3.2 pts (3/4, p = 1.000) |
