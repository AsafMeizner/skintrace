"""Consent-gated YouCam workflow. Transport is injected; importing makes no requests.

Transport contract: request(method, url, headers, body) returns a decoded JSON
object for API calls. Upload responses are ignored; transport must raise on HTTP
errors, disable redirects, enforce timeouts and never log secrets or signed URLs.
"""
import json
from urllib.parse import urlsplit, quote
from core import parse_result

BASE = 'https://yce-api-01.makeupar.com/s2s/v2.0'


class YouCamClient:
    def __init__(self, key, transport, *, allowed_upload_hosts=()):
        if not isinstance(key, str) or not key.strip():
            raise ValueError('API key required')
        self.key = key
        self.transport = transport
        self.allowed_upload_hosts = frozenset(allowed_upload_hosts)

    def _api(self, method, path, payload=None):
        body = None if payload is None else json.dumps(payload).encode()
        response = self.transport.request(method, BASE + path,
            {'Authorization': 'Bearer ' + self.key, 'Content-Type': 'application/json'}, body)
        if not isinstance(response, dict) or response.get('status') != 200:
            raise ValueError('API request failed')
        data = response.get('data')
        if not isinstance(data, dict):
            raise ValueError('Invalid API response')
        return response

    def start(self, image, content_type, *, consent=False):
        # Consent is checked before metadata registration or any image transfer.
        if consent is not True:
            raise ValueError('Explicit consent to send this photo to YouCam is required')
        if not isinstance(image, bytes) or not 0 < len(image) < 10 * 1024 * 1024:
            raise ValueError('Photo must be under 10 MB')
        if content_type not in ('image/jpeg', 'image/png'):
            raise ValueError('Only JPEG and PNG are supported')
        signature_ok = (image.startswith(b'\x89PNG\r\n\x1a\n') if content_type == 'image/png'
                        else image.startswith(b'\xff\xd8\xff'))
        if not signature_ok:
            raise ValueError('Photo format does not match its content type')
        response = self._api('POST', '/file', {'files': [{
            'content_type': content_type, 'file_name': 'photo.png' if content_type == 'image/png' else 'photo.jpg',
            'file_size': len(image)}]})
        files = response['data'].get('files')
        if not isinstance(files, list) or len(files) != 1 or not isinstance(files[0], dict):
            raise ValueError('Invalid upload metadata')
        file = files[0]
        file_id = file.get('file_id')
        requests = file.get('requests')
        if not isinstance(file_id, str) or not file_id or not isinstance(requests, list) or len(requests) != 1:
            raise ValueError('Invalid upload instructions')
        upload = requests[0]
        if not isinstance(upload, dict):
            raise ValueError('Invalid upload instructions')
        url = upload.get('url')
        if not isinstance(url, str):
            raise ValueError('Invalid upload destination')
        destination = urlsplit(url)
        if (destination.scheme != 'https' or destination.hostname not in self.allowed_upload_hosts
                or destination.username or destination.password or destination.port not in (None, 443)
                or destination.fragment or upload.get('method') != 'PUT'):
            raise ValueError('Upload destination is not approved')
        headers = upload.get('headers')
        if not isinstance(headers, dict):
            raise ValueError('Invalid upload headers')
        safe_headers = {}
        for name, value in headers.items():
            if not isinstance(name, str) or not isinstance(value, str) or '\r' in value or '\n' in value:
                raise ValueError('Invalid upload header')
            if name.lower() not in ('content-type', 'content-length'):
                raise ValueError('Unexpected upload header')
            if name.lower() in safe_headers:
                raise ValueError('Duplicate upload header')
            safe_headers[name.lower()] = value
        if safe_headers.get('content-type') != content_type or safe_headers.get('content-length') != str(len(image)):
            raise ValueError('Upload headers do not match photo')
        # Deliberately separate headers: API key never goes to storage.
        self.transport.request('PUT', url, safe_headers, image)
        task = self._api('POST', '/task/skin-analysis', {
            'src_file_id': file_id, 'dst_actions': ['texture', 'pore'], 'format': 'json'})
        task_id = task['data'].get('task_id')
        if not isinstance(task_id, str) or not task_id:
            raise ValueError('Missing task identifier')
        return task_id

    def poll_once(self, task_id):
        if not isinstance(task_id, str) or not task_id:
            raise ValueError('Missing task identifier')
        response = self._api('GET', '/task/skin-analysis/' + quote(task_id, safe=''))
        if response['data'].get('task_status') == 'running':
            return None
        return parse_result(response)
