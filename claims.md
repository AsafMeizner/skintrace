# SkinTrace claims (updated 2026-10-22)

| Claim | Where in the code | Shown in |
|---|---|---|
| Measures face scale, head turn/tilt, cheek colour, light direction from pixels | engine/measure.py: fingerprint_img | spike/results.md; demo/check_flow.py (stand-in fingerprints) |
| Noise floor (SD, MDC95) from repeats | spike/analyse.py -> engine/noise_floor.json | spike/results.md table |
| Refuses pairs whose capture conditions differ, with retake advice | engine/compare.py: gate, RETAKE | test_engine.py GateTests; spike/results.md (34 of 36 lighting-only pairs refused) |
| Thresholded change in left-versus-right cheek redness contrast; not lighting-controlled and does not assess bilateral changes or treatment effects | engine/compare.py: verdict | test_engine.py ChangeTests; spike/inject_results.md (synthetic only; no real positive-change validation) |
| /compare-photos keeps photos in memory | app.py: compare_photos | test_app.py ComparePhotosTests (no storage code path) |
| 36/36 false change, 2/36 contrast, P=0.96 | spike/analyse.py | spike/results.md |
| Injected-change validation, 2/120 false alarms | spike/inject_test.py | spike/inject_results.md (SYNTHETIC) |
| Optional YouCam upload/task/poll client | youcam.py, transport.py, app.py /analysis/* | test_youcam.py, test_transport.py (simulated service); one live run 2026-10-20 |
| Accepted backlit captures had higher mean YouCam scores without treatment (texture +29.9, moisture +29.2, radiance +19.9) | spike/youcam_noise.py (run once with the owner's written yes) -> engine/youcam_noise.json | spike/youcam-lighting-results.md (10 scored of 12; one person, one session; selection bias) |
| Judges a YouCam before/after against YouCam's own wobble | engine/scores.py: judge; app.py /judge-scores | test_scores.py, test_app.py JudgeScoresTests |
| YouCam quality errors become retake advice | youcam.py: RETAKE, YouCamTaskError; app.py | test_youcam.py ActionsAndErrorsTests |
| Gate is strict (refuses 57.9% of held-out same-condition pairs, 94.2% cross-light) | spike/heldout.py | spike/heldout-results.md |
| Pair accepted locally is scored by YouCam and judged against wobble; refused pair spends no units | app.py: run_youcam | test_app.py YouCamInComparisonTests (simulated YouCam; integrated /compare-photos upload path has NOT been exercised live; spike/youcam_noise.py tested a separate live client path) |
| Detects a real treatment effect | not built / not tested | |
| Works on other people, rooms or cameras | not tested (one person, one room) | |
| Journal, score ranges, saved results | not built | |
