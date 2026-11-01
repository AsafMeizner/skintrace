# Held-out gate refusal attribution — 2026-10-22

Diagnostic using the same 400 balanced 3-train/3-test splits as heldout.py. No threshold changes, no external calls. One person/session; overlapping appearances are dependent. These counts do not establish population performance.

| Gate | Same-condition failures / 2400 | Sole reason / 2400 | Cross-light failures / 3600 | Sole reason / 3600 |
|---|---:|---:|---:|---:|
| scale | 261 | 93 | 312 | 0 |
| yaw | 492 | 188 | 963 | 39 |
| roll_deg | 282 | 98 | 362 | 100 |
| pitch | 272 | 123 | 537 | 28 |
| face_L | 236 | 112 | 2212 | 382 |
| light_dir | 474 | 268 | 2528 | 450 |
| frame | 0 | 0 | 0 | 0 |

Multiple failures overlap, so columns must not be added. Sole-reason counts are the exact additional acceptances that removing just that gate would cause on these appearances; they are not a recommendation to remove it.

Total refusals: same 1390/2400; cross-light 3393/3600.

Decision: retain current thresholds. Choosing looser gates on this dataset would reuse evaluation data for tuning; any future candidate needs fresh held-out captures and real-positive validation before a reliability claim.
