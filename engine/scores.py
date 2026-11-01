"""Judge a change in YouCam raw scores against YouCam's own measured wobble (engine/youcam_noise.json).

The noise numbers come from one person's six front-lit captures; four backlit captures show how far scores
moved with light alone. Exploratory: not a clinical threshold. Pure arithmetic, no network.
"""
import json
from pathlib import Path

NOISE = json.loads((Path(__file__).parent / 'youcam_noise.json').read_text())['concerns']


def judge(before, after):
    """before/after: {concern: raw_score}. Returns one row per shared, known concern."""
    rows = []
    for name in sorted(before.keys() & after.keys()):
        n = NOISE.get(name)
        if n is None:
            continue
        change = round(after[name] - before[name], 2)
        beyond = abs(change) > n['mdc95']
        light_swing = n['back_minus_front']
        sensitive = abs(light_swing) > n['mdc95']
        if not beyond:
            verdict = 'within noise'
        elif sensitive and (change > 0) == (light_swing > 0):
            verdict = 'beyond noise, but light alone moved this score the same way'
        else:
            verdict = 'beyond noise'
        rows.append({'concern': name, 'change': change, 'mdc95': n['mdc95'], 'light_swing': light_swing,
                     'light_sensitive': sensitive, 'verdict': verdict})
    return rows


def summary():
    """The recorded experiment as a table, most light-sensitive first."""
    return sorted(({'concern': k, **v, 'light_sensitive': abs(v['back_minus_front']) > v['mdc95']} for k, v in NOISE.items()),
                  key=lambda r: -abs(r['back_minus_front']) / max(r['mdc95'], 0.01))
