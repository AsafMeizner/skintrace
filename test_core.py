import unittest
from core import parse_result


def result(output, status='success'):
    return {'data': {'task_status': status, 'results': {'output': output}}}


class ResultTests(unittest.TestCase):
    def test_completed_result(self):
        self.assertEqual(parse_result(result([{'type': 'wrinkle', 'raw_score': 72}])), {'wrinkle': 72.0})

    def test_official_json_example_uses_raw_not_ui_score(self):
        payload = result([
            {'type': 'texture', 'ui_score': 68, 'raw_score': 57.33},
            {'type': 'pore', 'ui_score': 92, 'raw_score': 95.34},
        ])
        self.assertEqual(parse_result(payload), {'texture': 57.33, 'pore': 95.34})

    def test_documented_score_boundaries(self):
        self.assertEqual(parse_result(result([
            {'type': 'texture', 'raw_score': 1},
            {'type': 'pore', 'raw_score': 100},
        ])), {'texture': 1.0, 'pore': 100.0})

    def test_malformed_containers_fail_cleanly(self):
        payloads = [None, [], {}, {'data': None}, {'data': []},
                    {'data': {'task_status': 'success', 'results': None}},
                    {'data': {'task_status': 'success', 'results': []}},
                    result({}), result([None]), result([[]]),
                    result([{'type': [], 'raw_score': 50}])]
        for payload in payloads:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                parse_result(payload)

    def test_pending_and_failed_are_not_scores(self):
        for status in ('running', 'error', None):
            with self.subTest(status=status), self.assertRaises(ValueError):
                parse_result(result([{'type': 'wrinkle', 'raw_score': 72}], status))

    def test_invalid_scores(self):
        for score in (True, False, None, '72', 0, 101, float('nan'), float('inf')):
            with self.subTest(score=score), self.assertRaises(ValueError):
                parse_result(result([{'type': 'wrinkle', 'raw_score': score}]))

    def test_empty_and_duplicate_results(self):
        for output in ([], None, [{'type': '', 'raw_score': 50}], [{'type': 'wrinkle', 'raw_score': 50}] * 2):
            with self.subTest(output=output), self.assertRaises(ValueError):
                parse_result(result(output))


if __name__ == '__main__':
    unittest.main()


def test_parse_result_skips_summary_items_from_live_api():
    # Shape observed in a real YouCam run on 2026-10-20 (values rounded).
    live = {'status': 200, 'data': {'task_status': 'success', 'results': {'output': [
        {'type': 'texture', 'ui_score': 75, 'raw_score': 67.35, 'mask_urls': []},
        {'type': 'pore', 'ui_score': 72, 'raw_score': 59.4, 'mask_urls': []},
        {'type': 'all', 'score': 73.5}, {'type': 'skin_age', 'score': 28},
        {'type': 'resize_image', 'mask_urls': []}]}}}
    from core import parse_result
    assert parse_result(live) == {'texture': 67.35, 'pore': 59.4}
