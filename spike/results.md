# SkinTrace spike results (real photos, local only, no vendor API)

Photos with a detected face: 23 of 25. Repeats: window-front n=6, window-behind n=6.

## Test-retest noise floor (same condition, 6 repeats): SD, MDC95 = 1.96*sqrt(2)*SD

| metric | front mean | front SD | behind mean | behind SD | pooled SD | MDC95 | front-behind diff | diff / MDC95 |
|---|---|---|---|---|---|---|---|---|
| scale | 0.34 | 0.05 | 0.34 | 0.03 | 0.04 | 0.11 | +0.00 | 0.0x |
| cx | 0.47 | 0.02 | 0.49 | 0.01 | 0.02 | 0.05 | -0.02 | 0.4x |
| roll_deg | -0.04 | 1.57 | -1.10 | 0.82 | 1.25 | 3.46 | +1.06 | 0.3x |
| yaw | 0.06 | 0.05 | 0.00 | 0.02 | 0.04 | 0.10 | +0.06 | 0.6x |
| pitch | 0.05 | 0.04 | 0.03 | 0.02 | 0.03 | 0.09 | +0.02 | 0.2x |
| left_cheek_L | 62.25 | 2.47 | 51.44 | 2.05 | 2.27 | 6.29 | +10.82 | 1.7x |
| left_cheek_a | 16.42 | 0.28 | 10.42 | 1.12 | 0.82 | 2.26 | +6.01 | 2.7x |
| right_cheek_a | 15.07 | 1.26 | 10.20 | 1.95 | 1.64 | 4.55 | +4.86 | 1.1x |
| light_dir | 0.10 | 0.02 | 0.02 | 0.02 | 0.02 | 0.07 | +0.09 | 1.3x |
| sharpness | 153.48 | 21.19 | 103.66 | 31.22 | 26.68 | 73.95 | +49.82 | 0.7x |
| contrast_a | 1.36 | 1.30 | 0.22 | 1.98 | 1.68 | 4.65 | +1.14 | 0.2x |
| face_L | 56.45 | 1.66 | 50.67 | 2.16 | 1.93 | 5.34 | +5.78 | 1.1x |
| face_a | 15.74 | 0.64 | 10.31 | 1.24 | 0.99 | 2.74 | +5.43 | 2.0x |

Reading: where diff/MDC95 > 1 the lighting swing alone produces a "change" the noise floor cannot explain. Zone-contrast (left minus right cheek) is the lighting-controlled quantity.

## Comparability gate on pairs

| pair type | pairs | judged comparable | refused (most common reason) |
|---|---|---|---|
| front-front | 15 | 7 | yaw |
| behind-behind | 15 | 15 | - |
| front-behind (lighting only) | 36 | 2 | light_dir |
| near-far (scale only) | 4 | 0 | scale |
| turn-left vs turn-right (pose) | 4 | 0 | yaw |

Criterion (c): mean fingerprint distance matched pairs 0.48 (n=30) vs mismatched 1.31 (n=44); P(matched < mismatched) = 0.96. Note the tolerances come from the same repeats (in-sample), so this is a spike result, not a generalisation claim.

## False "change" under lighting only (front vs behind pairs, 36 pairs)

- Naive redness (a*) difference exceeds noise floor in 36 of 36 lighting-only pairs (false "change").
- Left-minus-right contrast exceeds its own MDC95 in 2 of 36 lighting-only pairs.
- Gate refuses 34 of 36 of these pairs outright because face brightness/light direction differ.

## Rubbed-cheek set (cheek-now vs cheek-later), protocol mismatch known

- cheek-now-1.jpg vs cheek-later-1.jpg: NOT comparable: yaw differs by 0.37 (> MDC95 0.10); roll_deg differs by 5.48 (> MDC95 3.46); face not fully in frame
- cheek-now-1.jpg vs cheek-later-3.jpg: NOT comparable: roll_deg differs by 3.89 (> MDC95 3.46); face not fully in frame