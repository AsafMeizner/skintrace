"""Spike analysis on fingerprints.json (numbers only; no images are read here)."""
import json, itertools, math
import numpy as np
F = {k: v for k, v in json.load(open('fingerprints.json')).items() if v}
grp = lambda p: [v for k, v in F.items() if k.startswith(p)]
METRICS = ['scale', 'cx', 'roll_deg', 'yaw', 'pitch', 'left_cheek_L', 'left_cheek_a', 'right_cheek_a', 'light_dir', 'sharpness']
for v in F.values():
    v['contrast_a'] = v['left_cheek_a'] - v['right_cheek_a']      # left minus right cheek redness (control zone)
    v['face_L'] = (v['left_cheek_L'] + v['right_cheek_L']) / 2
    v['face_a'] = (v['left_cheek_a'] + v['right_cheek_a']) / 2
METRICS += ['contrast_a', 'face_L', 'face_a']
out = []
def table(name, g):
    arr = {m: np.array([x[m] for x in g]) for m in METRICS}
    return {m: (arr[m].mean(), arr[m].std(ddof=1)) for m in METRICS}
fr, bh = grp('window-front'), grp('window-behind')
nf, nb = table('front', fr), table('behind', bh)
out.append('# SkinTrace spike results (real photos, local only, no vendor API)\n')
out.append(f'Photos with a detected face: {len(F)} of 25. Repeats: window-front n={len(fr)}, window-behind n={len(bh)}.\n')
out.append('## Test-retest noise floor (same condition, 6 repeats): SD, MDC95 = 1.96*sqrt(2)*SD\n')
out.append('| metric | front mean | front SD | behind mean | behind SD | pooled SD | MDC95 | front-behind diff | diff / MDC95 |\n|---|---|---|---|---|---|---|---|---|')
floor = {}
for m in METRICS:
    sd = math.sqrt((nf[m][1] ** 2 + nb[m][1] ** 2) / 2)
    mdc = 1.96 * math.sqrt(2) * sd
    d = nf[m][0] - nb[m][0]
    floor[m] = {'sd': sd, 'mdc95': mdc}
    out.append(f'| {m} | {nf[m][0]:.2f} | {nf[m][1]:.2f} | {nb[m][0]:.2f} | {nb[m][1]:.2f} | {sd:.2f} | {mdc:.2f} | {d:+.2f} | {abs(d) / mdc:.1f}x |')
json.dump(floor, open('noise_floor.json', 'w'), indent=1)
out.append('\nReading: where diff/MDC95 > 1 the lighting swing alone produces a "change" the noise floor cannot explain. Zone-contrast (left minus right cheek) is the lighting-controlled quantity.\n')
# comparability gate: a pair is comparable if the capture-condition metrics differ by less than a tolerance derived from the floor
GATED = ['scale', 'yaw', 'roll_deg', 'pitch', 'face_L', 'light_dir']   # tolerance = the metric's own MDC95 from the repeats
def gate(a, b):
    why = [f'{m} differs by {abs(a[m]-b[m]):.2f} (> MDC95 {floor[m]["mdc95"]:.2f})' for m in GATED if abs(a[m] - b[m]) > floor[m]['mdc95']]
    if not (a['inside_frame'] and b['inside_frame']): why.append('face not fully in frame')
    return why
def distance(a, b):
    return math.sqrt(sum((abs(a[m] - b[m]) / floor[m]['mdc95']) ** 2 for m in GATED) / len(GATED))
def pairs(names):
    return [(a, b) for a, b in itertools.combinations(names, 2)]
sets = {'front-front': pairs([k for k in F if k.startswith('window-front')]),
        'behind-behind': pairs([k for k in F if k.startswith('window-behind')]),
        'front-behind (lighting only)': [(a, b) for a in F if a.startswith('window-front') for b in F if b.startswith('window-behind')],
        'near-far (scale only)': [(a, b) for a in F if a.startswith('near') for b in F if b.startswith('far')],
        'turn-left vs turn-right (pose)': [(a, b) for a in F if a.startswith('turn-left') for b in F if b.startswith('turn-right')]}
out.append('## Comparability gate on pairs\n')
out.append('| pair type | pairs | judged comparable | refused (most common reason) |\n|---|---|---|---|')
for name, ps in sets.items():
    ok = 0; reasons = {}
    for a, b in ps:
        w = gate(F[a], F[b])
        if not w: ok += 1
        for r in w: reasons[r.split(' ')[0]] = reasons.get(r.split(' ')[0], 0) + 1
    top = max(reasons, key=reasons.get) if reasons else '-'
    out.append(f'| {name} | {len(ps)} | {ok} | {top} |')
# false change test: for pairs judged comparable ... and raw vs contrast change in lighting-only pairs
matched = [distance(F[a], F[b]) for n in ('front-front', 'behind-behind') for a, b in sets[n]]
mism = [distance(F[a], F[b]) for n in ('front-behind (lighting only)', 'near-far (scale only)', 'turn-left vs turn-right (pose)') for a, b in sets[n]]
auc = sum((m < x) + 0.5 * (m == x) for m in matched for x in mism) / (len(matched) * len(mism))
out.append(f'\nCriterion (c): mean fingerprint distance matched pairs {np.mean(matched):.2f} (n={len(matched)}) vs mismatched {np.mean(mism):.2f} (n={len(mism)}); P(matched < mismatched) = {auc:.2f}. Note the tolerances come from the same repeats (in-sample), so this is a spike result, not a generalisation claim.')
out.append('\n## False "change" under lighting only (front vs behind pairs, 36 pairs)\n')
mdc_a, mdc_c = floor['face_a']['mdc95'], floor['contrast_a']['mdc95']
raw = [abs(F[b]['face_a'] - F[a]['face_a']) > mdc_a for a in F if a.startswith('window-front') for b in F if b.startswith('window-behind')]
con = [abs(F[b]['contrast_a'] - F[a]['contrast_a']) > mdc_c for a in F if a.startswith('window-front') for b in F if b.startswith('window-behind')]
out.append(f'- Naive redness (a*) difference exceeds noise floor in {sum(raw)} of {len(raw)} lighting-only pairs (false "change").')
out.append(f'- Left-minus-right contrast exceeds its own MDC95 in {sum(con)} of {len(con)} lighting-only pairs.')
out.append(f'- Gate refuses {sum(1 for a in F if a.startswith("window-front") for b in F if b.startswith("window-behind") if gate(F[a], F[b]))} of {len(raw)} of these pairs outright because face brightness/light direction differ.')
# cheek set: refused for pose?
out.append('\n## Rubbed-cheek set (cheek-now vs cheek-later), protocol mismatch known\n')
for a in [k for k in F if k.startswith('cheek-now')]:
    for b in [k for k in F if k.startswith('cheek-later')]:
        out.append(f'- {a} vs {b}: ' + ('comparable' if not gate(F[a], F[b]) else 'NOT comparable: ' + '; '.join(gate(F[a], F[b]))))
open('results.md', 'w').write('\n'.join(out)); print('\n'.join(out))
