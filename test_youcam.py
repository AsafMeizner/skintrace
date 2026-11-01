import copy
import unittest
from youcam import YouCamClient, BASE

PHOTO = b'\x89PNG\r\n\x1a\nmock-photo'
HOST = 'uploads.example.test'

class Transport:
    def __init__(self):
        self.calls = []
        self.metadata = {'status': 200, 'data': {'files': [{'file_id': 'file-1', 'requests': [{'url': 'https://' + HOST + '/photo?signature=test', 'method': 'PUT', 'headers': {'Content-Type': 'image/png', 'Content-Length': str(len(PHOTO))}}]}]}}
        self.result = {'status': 200, 'data': {'task_status': 'running'}}
        self.fail_upload = False
    def request(self, method, url, headers, body):
        self.calls.append((method, url, headers, body))
        if url == BASE + '/file':
            return copy.deepcopy(self.metadata)
        if method == 'PUT':
            if self.fail_upload:
                raise OSError('Upload failed')
            return None
        if method == 'POST':
            return {'status': 200, 'data': {'task_id': 'task-1'}}
        return self.result

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.transport = Transport()
        self.client = YouCamClient('test-placeholder', self.transport, allowed_upload_hosts=[HOST])
    def start(self, **kwargs):
        return self.client.start(PHOTO, 'image/png', **kwargs)
    def test_consent_required_before_any_request(self):
        for consent in (False, None, 1, 'true'):
            with self.assertRaises(ValueError):
                self.start(consent=consent)
        self.assertEqual(self.transport.calls, [])
    def test_workflow_and_credential_separation(self):
        self.assertEqual(self.start(consent=True), 'task-1')
        calls = self.transport.calls
        self.assertEqual([c[0] for c in calls], ['POST', 'PUT', 'POST'])
        self.assertEqual(calls[1][3], PHOTO)
        self.assertNotIn('authorization', {k.lower() for k in calls[1][2]})
        self.assertIn('Authorization', calls[0][2])
        self.assertIn('Authorization', calls[2][2])
    def test_unapproved_destinations_stop_before_upload(self):
        for url in ('http://' + HOST + '/x', 'https://evil.test/x', 'https://' + HOST + '.evil.test/x', 'https://user@' + HOST + '/x', 'https://' + HOST + ':444/x', 'https://' + HOST + '/x#fragment'):
            with self.subTest(url=url):
                self.transport.calls.clear()
                self.transport.metadata['data']['files'][0]['requests'][0]['url'] = url
                with self.assertRaises(ValueError):
                    self.start(consent=True)
                self.assertEqual(len(self.transport.calls), 1)
    def test_upload_headers_cannot_carry_credentials(self):
        self.transport.metadata['data']['files'][0]['requests'][0]['headers']['Authorization'] = 'untrusted'
        with self.assertRaises(ValueError):
            self.start(consent=True)
        self.assertEqual(len(self.transport.calls), 1)
    def test_wrong_size_stops_upload(self):
        self.transport.metadata['data']['files'][0]['requests'][0]['headers']['Content-Length'] = '1'
        with self.assertRaises(ValueError):
            self.start(consent=True)
        self.assertEqual(len(self.transport.calls), 1)
    def test_failed_upload_does_not_create_task(self):
        self.transport.fail_upload = True
        with self.assertRaises(OSError):
            self.start(consent=True)
        self.assertEqual(len(self.transport.calls), 2)
    def test_invalid_image_makes_no_requests(self):
        for photo, mime in ((b'', 'image/png'), (b'wrong', 'image/png'), (PHOTO, 'text/plain')):
            with self.assertRaises(ValueError):
                self.client.start(photo, mime, consent=True)
        self.assertEqual(self.transport.calls, [])
    def test_running_poll_and_path_encoding(self):
        self.assertIsNone(self.client.poll_once('task/with?separator'))
        self.assertTrue(self.transport.calls[0][1].endswith('task%2Fwith%3Fseparator'))
    def test_malformed_metadata_never_uploads(self):
        for files in (None, [], [{}], ['bad']):
            self.transport.calls.clear()
            self.transport.metadata['data']['files'] = files
            with self.assertRaises(ValueError):
                self.start(consent=True)
            self.assertEqual(len(self.transport.calls), 1)

if __name__ == '__main__':
    unittest.main()


class ActionsAndErrorsTests(unittest.TestCase):
    def test_unknown_or_repeated_concerns_rejected_before_any_call(self):
        from youcam import YouCamClient
        t = Transport()
        c = YouCamClient('k', t, allowed_upload_hosts=[HOST])
        for bad in (['nonsense'], ['pore', 'pore'], ['hd_pore']):
            with self.assertRaises(ValueError):
                c.start(PHOTO, 'image/png', consent=True, actions=bad)
        self.assertEqual(t.calls, [])

    def test_task_error_becomes_retake_advice(self):
        from youcam import YouCamClient, YouCamTaskError
        t = Transport()
        t.result = {'status': 200, 'data': {'task_status': 'error', 'error': 'error_src_face_too_small'}}
        c = YouCamClient('k', t, allowed_upload_hosts=[HOST])
        with self.assertRaises(YouCamTaskError) as ctx:
            c.poll_once('task1')
        self.assertIn('60%', ctx.exception.advice)
