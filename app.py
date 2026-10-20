"""Local SkinTrace demo. Live analysis is disabled unless a client is injected."""
import base64
import binascii
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from core import parse_result, compare


def sample(scores):
    return {'data': {'task_status': 'success', 'results': {'output': [{'type': k, 'raw_score': v} for k, v in scores.items()]}}}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Do not log photos, task identifiers or request contents.

    def reply(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        fonts = {'/fonts/newsreader.woff2': 'newsreader.woff2', '/fonts/schibsted-grotesk.woff2': 'schibsted-grotesk.woff2'}
        if self.path in fonts:
            body = (Path(__file__).parent / 'fonts' / fonts[self.path]).read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'font/woff2')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path != '/':
            self.send_error(404)
            return
        body = Path(__file__).with_name('index.html').read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path not in ('/compare', '/analysis/start', '/analysis/poll'):
            self.reply(404, {'error': 'Unknown request'})
            return
        # JSON-only requests prevent cross-site form submissions to this local service.
        if self.headers.get('Content-Type') != 'application/json':
            self.reply(415, {'error': 'JSON required'})
            return
        origin = self.headers.get('Origin')
        if origin and origin != 'http://' + self.headers.get('Host', ''):
            self.reply(403, {'error': 'Local page required'})
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            limit = 14 * 1024 * 1024 if self.path == '/analysis/start' else 4096
            if not 0 < length <= limit:
                raise ValueError()
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError()
            if self.path == '/compare':
                if payload.get('source', 'sample') == 'sample':
                    before, after = {'texture': 61, 'pore': 54}, {'texture': 66, 'pore': 52}
                elif payload.get('source') == 'photos':
                    before, after = payload.get('before'), payload.get('after')
                    if not isinstance(before, dict) or not isinstance(after, dict):
                        raise ValueError()
                else:
                    raise ValueError()
                result = compare(parse_result(sample(before)), parse_result(sample(after)), same_lighting=payload.get('lighting'), same_camera=payload.get('camera'), same_pose=payload.get('pose'))
            else:
                client = getattr(self.server, 'analysis_client', None)
                if client is None:
                    self.reply(503, {'error': 'Photo analysis is disabled pending approved access. Use the synthetic example.'})
                    return
                if self.path == '/analysis/start':
                    if payload.get('consent') is not True:
                        raise ValueError()
                    image = base64.b64decode(payload.get('image', ''), validate=True)
                    task = client.start(image, payload.get('content_type'), consent=True)
                    self.server.analysis_tasks.add(task)
                    result = {'task_id': task, 'status': 'running'}
                else:
                    task = payload.get('task_id')
                    if not isinstance(task, str) or task not in self.server.analysis_tasks:
                        raise ValueError()
                    scores = client.poll_once(task)
                    result = {'status': 'running'} if scores is None else {'status': 'success', 'scores': scores}
                    if scores is not None:
                        self.server.analysis_tasks.remove(task)
            self.reply(200, result)
        except (ValueError, AttributeError, TypeError, binascii.Error):
            self.reply(400, {'error': 'Invalid request. Check consent, photo format and task.'})
        except Exception:
            self.reply(502, {'error': 'Analysis service unavailable. No result was saved.'})


def make_server(address=('127.0.0.1', 8766), client=None):
    server = HTTPServer(address, Handler)
    server.analysis_client = client
    server.analysis_tasks = set()
    return server


if __name__ == '__main__':
    import os
    client = None
    if os.environ.get('SKINTRACE_LIVE') == '1' and os.environ.get('YOUCAM_API_KEY'):
        from youcam import YouCamClient
        from transport import HTTPTransport
        client = YouCamClient(os.environ['YOUCAM_API_KEY'], HTTPTransport(timeout=30),
                              allowed_upload_hosts=['yce-us.s3-accelerate.amazonaws.com'])
    print('SkinTrace: http://127.0.0.1:8766; live analysis ' + ('ENABLED (photos go to YouCam after consent)' if client else 'disabled'))
    make_server(client=client).serve_forever()
