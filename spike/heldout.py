"""Local split validation; no photos, network, dependencies or threshold tuning.
Calibrate on 3 repeats per light, evaluate exclusively on the other 3.
Enumerate all 20x20 balanced splits; these overlap and are NOT independent trials.
"""
import itertools, json, math, statistics
from pathlib import Path
root = Path(__file__).resolve().parent
raw = json.loads((root / 'fingerprints.json').read_text())
groups = [[dict(v) for k, v in sorted(raw.items()) if v and k.startswith(p)] for p in ('window-front', 'window-behind')]
for group in groups:
    for v in group:
        v['face_L'] = (v['left_cheek_L'] + v['right_cheek_L']) / 2
        v['face_a'] = (v['left_cheek_a'] + v['right_cheek_a']) / 2
        v['contrast_a'] = v['left_cheek_a'] - v['right_cheek_a']
gated = ['scale', 'yaw', 'roll_deg', 'pitch', 'face_L', 'light_dir']
metrics = gated + ['face_a', 'contrast_a']
rows = []
for ix in itertools.product(itertools.combinations(range(6), 3), repeat=2):
    train = [[v for i, v in enumerate(g) if i in ids] for g, ids in zip(groups, ix)]
    test = [[v for i, v in enumerate(g) if i not in ids] for g, ids in zip(groups, ix)]
    floor = {m: 1.96 * math.sqrt(sum(statistics.variance(v[m] for v in g) for g in train)) for m in metrics}
    def reject(a, b):
        return not (a['inside_frame'] and b['inside_frame']) or any(abs(a[m]-b[m]) > floor[m] for m in gated)
    same = [p for g in test for p in itertools.combinations(g, 2)]
    cross = list(itertools.product(*test))
    accepted = [(a,b) for a,b in cross if not reject(a,b)]
    rows.append({'same_refused':sum(reject(a,b) for a,b in same)/len(same),
                 'cross_refused':sum(reject(a,b) for a,b in cross)/len(cross),
                 'raw_cross_change':sum(abs(a['face_a']-b['face_a']) > floor['face_a'] for a,b in cross)/len(cross),
                 'contrast_cross_change':sum(abs(a['contrast_a']-b['contrast_a']) > floor['contrast_a'] for a,b in cross)/len(cross),
                 'accepted_cross':len(accepted),
                 'accepted_cross_change':sum(abs(a['contrast_a']-b['contrast_a']) > floor['contrast_a'] for a,b in accepted)})
lines = ['# Held-out local calibration sensitivity — 2026-10-22', '',
'One person, one capture session, six repeats per lighting condition. Each split calibrates solely on three photos per condition and evaluates on the other three. All 400 balanced splits are enumerated without tuning. Each evaluates six same-condition and nine cross-condition pairs.', '',
'Overlapping splits and pairs are dependent: these are sensitivity summaries, not 400 independent experiments or population confidence intervals.', '',
'| Measure | Mean across splits | Minimum | Maximum |', '|---|---:|---:|---:|']
for key in ['same_refused','cross_refused','raw_cross_change','contrast_cross_change']:
    values = [r[key] for r in rows]
    lines.append(f'| {key} | {statistics.mean(values):.1%} | {min(values):.1%} | {max(values):.1%} |')
accepted = sum(r['accepted_cross'] for r in rows)
changes = sum(r['accepted_cross_change'] for r in rows)
lines += ['', f'Across overlapping evaluations, {accepted}/3600 cross-condition pair appearances pass the gate; {changes} of those exceed the contrast threshold.', '',
'Interpretation: same-condition refusal measures usability loss. Cross-condition refusal measures capture mismatch detection, not detection of real skin changes. Contrast threshold exceedances under changed capture conditions cannot establish biological change. No real positive change was validated; no claim of clinical sensitivity, generalisation across people, or vendor integration follows. Thresholds remain research estimates.']
(root / 'heldout-results.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
