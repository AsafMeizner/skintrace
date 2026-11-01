"""Decide whether two capture fingerprints are comparable and whether one cheek really changed.

Pure arithmetic on numbers from engine/measure.py and the noise floor measured from repeated photos
(engine/noise_floor.json: SD and MDC95 per metric). No images and no vendor API here.
"""
import json
from pathlib import Path

NOISE = json.loads((Path(__file__).parent / 'noise_floor.json').read_text())
GATED = ['scale', 'yaw', 'roll_deg', 'pitch', 'face_L', 'light_dir']
RETAKE = {
    'scale': 'The face fills a different share of the frame. Hold the phone at the same distance as the first photo.',
    'yaw': 'The head is turned differently. Face the camera straight on, as in the first photo.',
    'roll_deg': 'The head is tilted differently. Keep the line of the eyes level, as in the first photo.',
    'pitch': 'The chin is higher or lower than in the first photo. Match the first photo.',
    'face_L': 'The face is lit more brightly or more dimly than in the first photo. Use the same light and time of day.',
    'light_dir': 'The light falls from a different side. Sit the same way to the same window or lamp.',
}


def fix(fp):
    """Derived quantities the engine compares."""
    fp = dict(fp)
    fp['face_L'] = (fp['left_cheek_L'] + fp['right_cheek_L']) / 2
    fp['face_a'] = (fp['left_cheek_a'] + fp['right_cheek_a']) / 2
    fp['contrast_a'] = fp['left_cheek_a'] - fp['right_cheek_a']
    return fp


def gate(a, b):
    """Reasons the pair cannot be compared; empty list = comparable."""
    why = []
    for m in GATED:
        diff, tol = abs(a[m] - b[m]), NOISE[m]['mdc95']
        if diff > tol:
            why.append({'metric': m, 'difference': round(diff, 3), 'tolerance': round(tol, 3), 'retake': RETAKE[m]})
    if not (a.get('inside_frame') and b.get('inside_frame')):
        why.append({'metric': 'frame', 'difference': None, 'tolerance': None,
                    'retake': 'The face is cut off by the edge of the photo. Keep the whole face in frame.'})
    return why


def verdict(before, after):
    before, after = fix(before), fix(after)
    why = gate(before, after)
    if why:
        return {'comparable': False, 'reasons': why, 'cheeks': None}
    d_left = after['left_cheek_a'] - before['left_cheek_a']
    d_right = after['right_cheek_a'] - before['right_cheek_a']
    contrast = d_left - d_right
    thr = NOISE['contrast_a']['mdc95']
    if contrast > thr:
        call = 'left cheek redder than the other cheek, beyond the noise floor'
    elif contrast < -thr:
        call = 'right cheek redder than the other cheek, beyond the noise floor'
    else:
        call = 'no left-versus-right redness difference beyond the noise floor'
    shared = (d_left + d_right) / 2
    shared_note = None
    if abs(shared) > NOISE['face_a']['mdc95']:
        shared_note = (f'Both cheeks moved together by {shared:+.1f}. Lighting, colour balance or a real '
                       'change affecting both cheeks could cause this. This comparison measures only '
                       'the difference between cheeks and cannot tell those causes apart.')
    return {'comparable': True, 'reasons': [],
            'cheeks': {'shared_shift_note': shared_note, 'left_a_change': round(d_left, 2), 'right_a_change': round(d_right, 2),
                       'contrast_change': round(contrast, 2), 'noise_floor_mdc95': round(thr, 2), 'verdict': call}}
