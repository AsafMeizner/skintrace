# SkinTrace

Skin-analysis scores move with the window, the distance and the angle of the head. SkinTrace measures those capture conditions from the pixels of two selfies, before anything is compared, and then either names a change or says exactly how to retake.

Everything below runs locally. Photos are read in memory by the app and are not saved or sent anywhere. With a YouCam key on the server and the user's consent, a pair that passes the local check is also scored by YouCam (15 SD concerns, `/compare-photos` with `youcam: true`) and each concern's change is judged against YouCam's measured wobble; a pair the local check refuses spends no YouCam units. Without a key the page says YouCam is off. This path is tested with a simulated YouCam service (`test_app.py`), and was exercised live once on the experiment below.

## What it computes (`engine/`)

1. `engine/measure.py`: per photo, from MediaPipe FaceMesh landmarks (local, bundled model) and OpenCV: face scale and position, head roll/yaw/pitch, L*a*b* medians of left cheek, right cheek and forehead polygons, light direction (left vs right cheek brightness), sharpness.
2. `engine/noise_floor.json`: test-retest SD and MDC95 (1.96 x sqrt(2) x SD) per metric, from six same-condition repeats in each of two lighting set-ups (`spike/analyse.py`).
3. `engine/compare.py: gate`: a pair is "not comparable" if scale, yaw, roll, pitch, face brightness or light direction differs by more than that metric's MDC95, or a face is cut off. Each reason carries retake advice.
4. `engine/compare.py: verdict`: if comparable, the change in left-cheek a* minus right-cheek a* (so a shift of both cheeks together is reported separately, not as a one-cheek change) is judged against its own MDC95: "left cheek redder", "right cheek redder" or "no left-versus-right redness difference beyond the noise floor".

## YouCam's own score wobble (`engine/scores.py`, `engine/youcam_noise.json`)

With the owner's written yes, 12 face crops (six front-lit, six backlit, no treatment) went through YouCam's SD skin analysis (15 concerns); 10 were scored, two backlit ones rejected as too dark. Per concern: SD and exploratory MDC95 from the front-lit captures, and how far accepted backlit captures moved. Texture +29.9, moisture +29.2, radiance +19.9 from light alone. `/judge-scores` compares a before/after pair of YouCam raw scores against that wobble ("within noise", "beyond noise", or "beyond noise, but light alone moved this score the same way"). One person, one session, selection bias from the rejected photos, exploratory thresholds (`spike/youcam-lighting-results.md`). Raw per-photo scores are not in this repository.

## Evidence (one person, one room; see `spike/`)

- 12 photos, 36 window-front vs window-behind pairs (skin unchanged): naive redness change exceeds the noise floor in 36/36; the gate refuses 34/36; the left-versus-right cheek contrast exceeds its floor in 2/36 (a contrast, not a lighting control) (`spike/results.md`).
- Matched pairs are closer than mismatched pairs, P(matched < mismatched) = 0.96, with tolerances taken from the same repeats (in-sample).
- Synthetic validation: a known redness added in pixels to one cheek of real photos is flagged on that cheek and never on the other; 2 false alarms in 120 pairs (`spike/inject_results.md`).
- Not done: a test on a real treatment or concealer. The rubbed-cheek photos were too turned and cut off, and the gate refused them. No photos or per-photo numbers are in this repository.

## Run

```sh
pip install -r requirements-engine.txt   # mediapipe, opencv, numpy<2 (optional; only for measuring photos)
python3 app.py                            # http://127.0.0.1:8766
python3 -m unittest discover -v           # 58 tests, no photos, no network
python3 demo/check_flow.py                # browser check with stand-in fingerprints (needs Playwright)
```

Without the optional packages the page loads and `/compare-photos` answers 503 with the reason.

## Limits

Cosmetic colour readings, not diagnoses. A measured change cannot show that a product caused it. Face landmarks need a roughly frontal, fully visible face. Thresholds come from one person's repeats. The contrast detector only sees a left-versus-right difference larger than 4.65 a* units.

## Optional YouCam client

`SKINTRACE_LIVE=1 YOUCAM_API_KEY=<key> python3 app.py` enables `/analysis/start` and `/analysis/poll` (upload, task, poll; consent required; the key is read from the environment). Verified once on 2026-10-20 with one consenting adult's selfie (raw scores texture 67.4, pore 59.4). It is not used by the engine.

MIT licence; see LICENSE.
