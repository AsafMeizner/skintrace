"""Offline YouCam result parsing. No network calls or medical conclusions."""
from math import isfinite


def parse_result(payload):
    if not isinstance(payload, dict):
        raise ValueError('Invalid response object')
    data = payload.get('data', {})
    if not isinstance(data, dict):
        raise ValueError('Invalid response data')
    status = data.get('task_status')
    if status != 'success':
        raise ValueError('Analysis is not successful: ' + str(status))
    results = data.get('results')
    if not isinstance(results, dict):
        raise ValueError('Missing analysis results')
    output = results.get('output')
    if not isinstance(output, list) or not output:
        raise ValueError('Missing analysis output')
    scores = {}
    for item in output:
        if not isinstance(item, dict):
            raise ValueError('Invalid analysis item')
        concern = item.get('type')
        if not isinstance(concern, str) or not concern or concern in scores:
            raise ValueError('Missing or duplicate concern')
        if 'raw_score' not in item:
            continue  # live API also returns summary items (all, skin_age, resize_image) without raw_score
        score = item.get('raw_score')
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not isfinite(score) or not 1 <= score <= 100:
            raise ValueError('Invalid raw score')
        scores[concern] = float(score)
    if not scores:
        raise ValueError('No raw scores in analysis output')
    return scores


def compare(before, after, *, same_lighting, same_camera, same_pose):
    """Describe score changes only when capture conditions match by user report."""
    if not all(value is True for value in (same_lighting, same_camera, same_pose)):
        return {'comparable': False, 'reason': 'Retake both photos with matching lighting, camera and pose.', 'changes': {}}
    common = before.keys() & after.keys()
    if not common:
        raise ValueError('No shared skin concerns')
    return {'comparable': True, 'changes': {key: round(after[key] - before[key], 2) for key in sorted(common)}, 'note': 'Higher raw scores mean more favorable cosmetic assessments. Changes do not establish treatment effects or medical improvement.'}
