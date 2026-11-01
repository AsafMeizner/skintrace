import glob, json, os, sys
from fingerprint import fingerprint
src = sys.argv[1]
res = {}
for f in sorted(glob.glob(os.path.join(src, '*.jpg'))):
    res[os.path.basename(f)] = fingerprint(f)
json.dump(res, open('fingerprints.json', 'w'), indent=1)
for k, v in res.items():
    print(k, 'NO FACE' if v is None else ' '.join(f'{a}={b:.2f}' if isinstance(b, float) else f'{a}={b}' for a, b in v.items() if a in ('scale','cx','inside_frame','left_cheek_L','light_dir','sharpness','roll_deg','yaw','pitch','left_cheek_a','right_cheek_a')))
