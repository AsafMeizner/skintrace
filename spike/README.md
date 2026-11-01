# SkinTrace spike: can the product measure comparability itself? (2026-10-22)

Question: skin-analysis scores move with lighting, distance and pose. Can we decide from the pixels alone whether two selfies are comparable, and separate a real local change from a lighting swing, with no vendor call?

Data: 25 selfies by the owner (consent: local use only, never uploaded, never committed). 23 had a detectable face. Only numeric summaries are kept in this folder (`results.md`, `noise_floor.json`, `inject_results.md`); per-photo numbers (`fingerprints.json`) stay out of git.

Engine under test (`fingerprint.py`, `analyse.py`, `inject_test.py`), all local (MediaPipe FaceMesh with its bundled model, OpenCV, NumPy):
1. **Fingerprint** per photo: face scale/position, roll/yaw/pitch from landmarks, L*a*b* medians of left cheek, right cheek and forehead polygons, light direction (left vs right cheek brightness), sharpness.
2. **Noise floor** from six same-condition repeats: SD and MDC95 = 1.96 x sqrt(2) x SD per metric.
3. **Comparability gate**: a pair is "not comparable" if any capture metric (scale, yaw, roll, pitch, face brightness, light direction) differs by more than its own MDC95, or the face leaves the frame. The reason is named.
4. **Lighting-controlled change detector**: change in (left cheek a* minus right cheek a*), judged against the contrast's own MDC95, so a lighting swing that reddens both cheeks cancels.

Pass criteria (written before running): (a) lighting-only pairs show no false change; (b) a change on one cheek is flagged and the other cheek is not; (c) matched pairs differ less than mismatched pairs.

Results (see `results.md`, `inject_results.md`):
- (a) PASS on real photos: window-front vs window-behind (36 pairs): naive redness change exceeds the noise floor in 36/36; the gate refuses 34/36; the left-versus-right cheek contrast exceeds its floor in 2/36 (a contrast, not a lighting control).
- (c) PASS in-sample: mean distance 0.48 (matched, n=30) vs 1.31 (mismatched, n=44); P(matched < mismatched) = 0.96. Tolerances come from the same repeats, so this is not a generalisation claim.
- (b) PASS on a SYNTHETIC injection only: +a* added to one cheek of real photos in pixels; false alarms at +0: 2/120; the injected cheek is flagged 8/60 at +2, 21/60 at +4, 38/60 at +6, 50/60 at +8 (left) and 9, 22, 39, 52 (right); the other cheek is never flagged. A real concealed/rubbed cheek test was NOT possible: the owner's rubbed-cheek photos are strongly yawed and partly out of frame, and the gate correctly refuses them as not comparable.

Limits: one person, one room, 25 photos; thresholds are in-sample; the contrast's MDC95 is 4.65 a* units, so only a sizeable local redness change is detectable; nothing here measures a skincare effect.
