import unittest
from engine import scores


class ScoreJudgeTests(unittest.TestCase):
    def test_small_change_is_within_noise(self):
        row = scores.judge({'wrinkle': 80}, {'wrinkle': 83})[0]
        self.assertEqual(row['verdict'], 'within noise')

    def test_change_beyond_noise_in_light_sensitive_concern_is_flagged(self):
        row = scores.judge({'texture': 55}, {'texture': 80})[0]
        self.assertEqual(row['verdict'], 'beyond noise, but light alone moved this score the same way')

    def test_change_beyond_noise_opposite_to_light_swing_is_plain(self):
        row = scores.judge({'texture': 80}, {'texture': 55})[0]
        self.assertEqual(row['verdict'], 'beyond noise')

    def test_unknown_or_unshared_concerns_are_skipped(self):
        self.assertEqual(scores.judge({'made_up': 1, 'pore': 50}, {'made_up': 90}), [])

    def test_summary_lists_all_recorded_concerns_most_swung_first(self):
        s = scores.summary()
        self.assertEqual(len(s), 15)
        self.assertEqual(s[0]['concern'], 'moisture')  # largest light swing in units of its own noise


if __name__ == '__main__':
    unittest.main()
