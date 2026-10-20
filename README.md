# SkinTrace

A local prototype that checks capture conditions before comparing cosmetic skin scores.

## Run

Requires Python 3.10 or newer. The synthetic demo needs no packages or API key.

```sh
python3 app.py
```

Open http://127.0.0.1:8766. Leave a capture-condition box unchecked and compare to see the pause state. Confirm lighting, camera and pose to see the invented texture +5 and pore -2 differences.

## Implemented behavior

- Validates completed results and raw scores from 1–100; higher scores are more favorable.
- Compares shared concerns only after explicit lighting, camera and pose confirmations.
- Provides consent-gated photo controls, clears stale results when photos change, and supports two-result comparison.
- Includes an HTTPS upload/task/poll client and local HTTP routes tested with simulated service responses. Live analysis (verified once, see below) is disabled by default; running the command above never enables it.
- Keeps credentials out of the browser and avoids logging photos or request contents.

## Current limits

Live verified once: on 2026-10-20 the client ran a full upload, skin-analysis task and poll against the real YouCam API with one consenting adult's selfie (not included in this repository). It returned raw scores texture 67.4 and pore 59.4 (higher is more favorable; the ui_score shown by YouCam, 75 and 72, is adjusted and not used for comparison). That run found the API also returns summary items without raw_score (all, skin_age, resize_image); the parser now skips them (covered by a test). Only that single run was made; the default application still makes no external calls and its demo scores are invented.

Capture confirmations are user statements, not scientific validation. Cosmetic scores are not diagnoses, and score differences cannot prove treatment effects. The local server is a development prototype, not a public hosting configuration.

## Verification

```sh
python3 -m unittest discover -v
python3 demo/check_flow.py
```

The browser check requires Playwright, Chromium and the local application running. It exercises the blocked and confirmed synthetic comparison and disabled-live disclosure. Automated tests cover score parsing, comparison, consent, upload/task handling, transport and local HTTP behavior.

## Prototype video

`demo/storyboard.yaml` and `demo/check_flow.py` reproduce the synthetic walkthrough. The corrected local render is 95.7 seconds at 1920 × 1080, with original offline narration and music. It repeatedly discloses invented scores and pending live validation. It is a prototype preview, not the final submission video.

## License

MIT; see LICENSE.

## Optional live mode

`SKINTRACE_LIVE=1 YOUCAM_API_KEY=<your key> python3 app.py` enables photo analysis. Photos are sent to YouCam only after the consent box is ticked. The key is read from the environment and never stored.
