"""Engine tests on SYNTHETIC numeric fingerprints plus the real aggregate noise floor (no photos)."""
import unittest
from engine import compare

BASE = {'scale': .34, 'cx': .5, 'cy': .5, 'inside_frame': True, 'roll_deg': 0.0, 'yaw': 0.02, 'pitch': 0.03,
        'left_cheek_L': 56.0, 'right_cheek_L': 55.0, 'left_cheek_a': 15.0, 'right_cheek_a': 15.0, 'light_dir': 0.01}


def fp(**kw):
    return {**BASE, **kw}


class GateTests(unittest.TestCase):
    def test_identical_capture_is_comparable(self):
        self.assertEqual(compare.gate(compare.fix(BASE), compare.fix(BASE)), [])

    def test_brighter_light_refuses_with_retake_advice(self):
        out = compare.verdict(BASE, fp(left_cheek_L=66.0, right_cheek_L=65.0))
        self.assertFalse(out['comparable'])
        self.assertIn('face_L', [r['metric'] for r in out['reasons']])
        self.assertIn('same light', ' '.join(r['retake'] for r in out['reasons']))

    def test_turned_head_and_distance_each_named(self):
        out = compare.verdict(BASE, fp(yaw=0.5, scale=0.6))
        self.assertEqual({r['metric'] for r in out['reasons']}, {'yaw', 'scale'})

    def test_face_cut_off_refuses(self):
        out = compare.verdict(BASE, fp(inside_frame=False))
        self.assertEqual([r['metric'] for r in out['reasons']], ['frame'])


class ChangeTests(unittest.TestCase):
    def test_both_cheeks_shifting_together_is_not_a_cheek_change(self):
        out = compare.verdict(BASE, fp(left_cheek_a=18.0, right_cheek_a=18.0))
        self.assertTrue(out['comparable'])
        self.assertEqual(out['cheeks']['verdict'], 'no left-versus-right redness difference beyond the noise floor')

    def test_one_cheek_redder_beyond_floor_is_named(self):
        big = compare.NOISE['contrast_a']['mdc95'] + 1.0
        left = compare.verdict(BASE, fp(left_cheek_a=15.0 + big))
        right = compare.verdict(BASE, fp(right_cheek_a=15.0 + big))
        self.assertIn('left cheek redder', left['cheeks']['verdict'])
        self.assertIn('right cheek redder', right['cheeks']['verdict'])

    def test_shared_shift_is_reported_and_not_called_a_change(self):
        out = compare.verdict(BASE, fp(left_cheek_a=15.0 - 6.5, right_cheek_a=15.0 - 6.0))
        self.assertEqual(out['cheeks']['verdict'], 'no left-versus-right redness difference beyond the noise floor')
        self.assertIn('Both cheeks moved together', out['cheeks']['shared_shift_note'])
        self.assertIn('a real change affecting both cheeks', out['cheeks']['shared_shift_note'])
        self.assertIn('cannot tell those causes apart', out['cheeks']['shared_shift_note'])
        self.assertIsNone(compare.verdict(BASE, fp())['cheeks']['shared_shift_note'])

    def test_small_difference_is_within_noise(self):
        out = compare.verdict(BASE, fp(left_cheek_a=15.0 + compare.NOISE['contrast_a']['mdc95'] / 2))
        self.assertEqual(out['cheeks']['verdict'], 'no left-versus-right redness difference beyond the noise floor')

    def test_noise_floor_is_the_measured_file(self):
        self.assertEqual(set(compare.GATED) - set(compare.NOISE), set())
        self.assertGreater(compare.NOISE['contrast_a']['mdc95'], 0)


if __name__ == '__main__':
    unittest.main()
