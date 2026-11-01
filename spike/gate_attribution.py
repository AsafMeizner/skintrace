"""Held-out refusal attribution, diagnostic only; never tunes production thresholds."""
import itertools, json, math, statistics
from collections import Counter
from pathlib import Path
root=Path(__file__).resolve().parent
raw=json.loads((root/'fingerprints.json').read_text())
groups=[[dict(v) for k,v in sorted(raw.items()) if v and k.startswith(p)] for p in ('window-front','window-behind')]
metrics=['scale','yaw','roll_deg','pitch','face_L','light_dir']
for group in groups:
    for v in group:
        v['face_L']=(v['left_cheek_L']+v['right_cheek_L'])/2
counts={kind:Counter() for kind in ('same','cross')}
for ids in itertools.product(itertools.combinations(range(6),3),repeat=2):
    train=[[v for i,v in enumerate(g) if i in ix] for g,ix in zip(groups,ids)]
    test=[[v for i,v in enumerate(g) if i not in ix] for g,ix in zip(groups,ids)]
    floor={m:1.96*math.sqrt(sum(statistics.variance(v[m] for v in g) for g in train)) for m in metrics}
    for kind,pairs in [('same',[p for g in test for p in itertools.combinations(g,2)]),('cross',list(itertools.product(*test)))]:
        for a,b in pairs:
            failures=[m for m in metrics if abs(a[m]-b[m])>floor[m]]
            if not(a['inside_frame'] and b['inside_frame']): failures.append('frame')
            c=counts[kind]; c['pairs']+=1; c['refused']+=bool(failures)
            for m in failures:
                c[m]+=1
                if len(failures)==1: c[m+'_sole']+=1
lines=['# Held-out gate refusal attribution — 2026-10-22','','Diagnostic using the same 400 balanced 3-train/3-test splits as heldout.py. No threshold changes, no external calls. One person/session; overlapping appearances are dependent. These counts do not establish population performance.','','| Gate | Same-condition failures / 2400 | Sole reason / 2400 | Cross-light failures / 3600 | Sole reason / 3600 |','|---|---:|---:|---:|---:|']
for m in metrics+['frame']:
    lines.append(f"| {m} | {counts['same'][m]} | {counts['same'][m+'_sole']} | {counts['cross'][m]} | {counts['cross'][m+'_sole']} |")
lines+=['','Multiple failures overlap, so columns must not be added. Sole-reason counts are the exact additional acceptances that removing just that gate would cause on these appearances; they are not a recommendation to remove it.','',f"Total refusals: same {counts['same']['refused']}/{counts['same']['pairs']}; cross-light {counts['cross']['refused']}/{counts['cross']['pairs']}.",'','Decision: retain current thresholds. Choosing looser gates on this dataset would reuse evaluation data for tuning; any future candidate needs fresh held-out captures and real-positive validation before a reliability claim.']
(root/'gate-attribution-results.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
