import base64
import http.client
import json
import threading
import unittest
from app import make_server
from youcam import YouCamClient
from test_youcam import Transport, HOST, PHOTO


class AppTests(unittest.TestCase):
    def setUp(self):
        self.transport = Transport()
        self.server = make_server(('127.0.0.1', 0), YouCamClient('test-placeholder', self.transport, allowed_upload_hosts=[HOST]))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def post(self, path, payload, origin=None):
        conn = http.client.HTTPConnection(*self.server.server_address, timeout=3)
        headers = {'Content-Type': 'application/json'}
        if origin:
            headers['Origin'] = origin
        conn.request('POST', path, json.dumps(payload), headers)
        response = conn.getresponse()
        status, data = response.status, json.loads(response.read())
        conn.close()
        return status, data

    def photo(self, consent=True):
        return {'image': base64.b64encode(PHOTO).decode(), 'content_type': 'image/png', 'consent': consent}

    def test_font_allowlist(self):
        for path, expected in [('/fonts/newsreader.woff2', 200), ('/fonts/schibsted-grotesk.woff2', 200), ('/fonts/../app.py', 404)]:
            conn = http.client.HTTPConnection(*self.server.server_address, timeout=3)
            conn.request('GET', path)
            response = conn.getresponse()
            self.assertEqual(response.status, expected)
            if expected == 200:
                self.assertEqual(response.getheader('Content-Type'), 'font/woff2')
                self.assertGreater(len(response.read()), 1000)
            else:
                response.read()
            conn.close()

    def test_full_mocked_workflow(self):
        status, started = self.post('/analysis/start', self.photo())
        self.assertEqual(status, 200)
        self.assertEqual(len(self.transport.calls), 3)
        self.assertEqual(self.post('/analysis/poll', started), (200, {'status': 'running'}))
        self.transport.result = {'status': 200, 'data': {'task_status': 'success', 'results': {'output': [{'type': 'texture', 'raw_score': 66}]}}}
        self.assertEqual(self.post('/analysis/poll', started), (200, {'status': 'success', 'scores': {'texture': 66.0}}))
        self.assertEqual(self.post('/analysis/poll', started)[0], 400)

    def test_photo_comparison_validates_scores_and_conditions(self):
        payload = {'source': 'photos', 'before': {'texture': 42, 'pore': 60}, 'after': {'texture': 49}, 'lighting': True, 'camera': True, 'pose': True}
        status, result = self.post('/compare', payload)
        self.assertEqual(status, 200)
        self.assertEqual(result['changes'], {'texture': 7})
        payload['pose'] = False
        self.assertFalse(self.post('/compare', payload)[1]['comparable'])
        for bad in (None, {}, {'texture': True}, {'texture': 101}, {'texture': '50'}):
            payload['after'] = bad
            self.assertEqual(self.post('/compare', payload)[0], 400)
        self.assertEqual(self.transport.calls, [])

    def test_no_consent_no_network(self):
        self.assertEqual(self.post('/analysis/start', self.photo(False))[0], 400)
        self.assertEqual(self.transport.calls, [])

    def test_default_disabled_no_network(self):
        self.server.analysis_client = None
        self.assertEqual(self.post('/analysis/start', self.photo())[0], 503)
        self.assertEqual(self.transport.calls, [])

    def test_cross_origin_and_unknown_task_no_network(self):
        self.assertEqual(self.post('/analysis/start', self.photo(), 'https://other.example')[0], 403)
        self.assertEqual(self.post('/analysis/poll', {'task_id': 'unknown'})[0], 400)
        self.assertEqual(self.transport.calls, [])

    def test_upstream_errors_are_redacted(self):
        self.transport.fail_upload = True
        status, result = self.post('/analysis/start', self.photo())
        self.assertEqual(status, 502)
        self.assertNotIn('signature', json.dumps(result))
        self.assertEqual(self.server.analysis_tasks, set())


if __name__ == '__main__':
    unittest.main()
