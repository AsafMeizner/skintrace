"""Synthetic validation (labelled): add a known a* (redness) shift to ONE cheek of a real photo, then ask
the detector whether the zone-contrast moved beyond the noise floor. Pairs are real repeats of one condition.
Not evidence of a real skincare effect: it checks sensitivity, false alarms and which cheek is flagged."""
import json, sys, itertools, math
from fingerprint import load, landmarks, fingerprint_img
floor = json.load(open('noise_floor.json'))
src = sys.argv[1]
names = [f'window-behind-{i}.jpg' for i in range(1, 7)] + [f'window-front-{i}.jpg' for i in range(1, 7)]
base = {}
for n in names:
    img = load(f'{src}/{n}'); pts = landmarks(img)
    base[n] = (img, pts)
def flagged(before, after):
    """Return per-cheek flags: zone a* change minus the other cheek's change (lighting control) vs MDC of the contrast."""
    d_left = after['left_cheek_a'] - before['left_cheek_a']; d_right = after['right_cheek_a'] - before['right_cheek_a']
    contrast = d_left - d_right
    thr = floor['contrast_a']['mdc95']
    return ('left' if contrast > thr else 'right' if contrast < -thr else 'none'), contrast
groups = {'behind': [n for n in names if 'behind' in n], 'front': [n for n in names if 'front' in n]}
rows = ['| injected a* shift on LEFT cheek | pairs | flagged left | flagged right | flagged none |', '|---|---|---|---|---|']
rows_r = ['| injected a* shift on RIGHT cheek | pairs | flagged left | flagged right | flagged none |', '|---|---|---|---|---|']
for zone, tbl in (('left_cheek', rows), ('right_cheek', rows_r)):
    for delta in (0, 2, 4, 6, 8):
        cnt = {'left': 0, 'right': 0, 'none': 0}; n = 0
        for g in groups.values():
            for a, b in itertools.permutations(g, 2):
                before = fingerprint_img(*base[a]); after = fingerprint_img(*base[b], inject=(zone, delta))
                cnt[flagged(before, after)[0]] += 1; n += 1
        tbl.append(f'| +{delta} | {n} | {cnt["left"]} | {cnt["right"]} | {cnt["none"]} |')
text = '\n'.join(['# Injected-change validation (synthetic, labelled; real photos, pairs of same-condition repeats, 60 ordered pairs per row)', f'Detector: change in (left a* - right a*) beyond contrast MDC95 = {floor["contrast_a"]["mdc95"]:.2f}. Delta 0 = false-alarm rate.', ''] + rows + [''] + rows_r)
open('inject_results.md', 'w').write(text); print(text)
