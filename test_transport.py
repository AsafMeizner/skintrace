import io
import unittest
from urllib.error import HTTPError
from transport import HTTPTransport, NoRedirect

class Response(io.BytesIO):
    status = 200

class Opener:
    def __init__(self, body=b'{"status":200}'):
        self.body = body
        self.calls = []
    def open(self, request, timeout):
        self.calls.append((request, timeout))
        return Response(self.body)

class TransportTests(unittest.TestCase):
    def test_json_and_timeout(self):
        opener = Opener()
        transport = HTTPTransport(opener=opener, timeout=7)
        self.assertEqual(transport.request('GET', 'https://example.test/api', {}, None), {'status': 200})
        self.assertEqual(opener.calls[0][1], 7)
    def test_size_bound(self):
        transport = HTTPTransport(opener=Opener(b'x' * 11), max_response_bytes=10)
        with self.assertRaises(ValueError):
            transport.request('GET', 'https://example.test/api', {}, None)
    def test_invalid_json_or_container(self):
        for body in (b'not json', b'[]', b'null', b'\xff'):
            with self.subTest(body=body), self.assertRaises(ValueError):
                HTTPTransport(opener=Opener(body)).request('GET', 'https://example.test/api', {}, None)
    def test_upload_response_is_not_parsed(self):
        self.assertIsNone(HTTPTransport(opener=Opener(b'')).request('PUT', 'https://example.test/photo', {}, b'photo'))
    def test_invalid_destinations_never_open(self):
        opener = Opener()
        for url in ('http://example.test', 'https://user@example.test', 'https://example.test:444', 'https://example.test/#x'):
            with self.assertRaises(ValueError):
                HTTPTransport(opener=opener).request('GET', url, {}, None)
        self.assertEqual(opener.calls, [])
    def test_redirect_handler_refuses_followup(self):
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, 'redirect', {}, 'https://other.test'))

if __name__ == '__main__':
    unittest.main()
