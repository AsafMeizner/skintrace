"""Offline YouCam result parsing. No network calls or medical conclusions. Photo comparison lives in engine/."""
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
