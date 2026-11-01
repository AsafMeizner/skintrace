"""Local SkinTrace demo. Live analysis is disabled unless a client is injected."""
import base64
import binascii
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from core import parse_result
from youcam import YouCamTaskError
from engine import scores as engine_scores
from engine import compare as engine_compare


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
        if self.path == '/youcam-noise':
            self.reply(200, {'concerns': engine_scores.summary()})
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

    def run_youcam(self, images, types, comparable):
        """Spend YouCam units only on a pair the local gate accepts. Returns {'status', ...}."""
        client = getattr(self.server, 'analysis_client', None)
        if client is None:
            return {'status': 'off', 'message': 'YouCam analysis is off: start the server with a YouCam key to enable it.'}
        if not comparable:
            return {'status': 'skipped', 'message': 'The local gate refused this pair, so no YouCam units were spent. Retake first.'}
        sets = []
        try:
            for data, kind in zip(images, types):
                task = client.start(data, kind, consent=True, actions=list(engine_scores.NOISE))
                for _ in range(40):
                    result = client.poll_once(task)
                    if result is not None:
                        sets.append(result)
                        break
                    self.server.sleep(2)
                else:
                    return {'status': 'timeout', 'message': 'YouCam did not finish in time. Try again later.'}
        except YouCamTaskError as error:
            return {'status': 'refused_by_youcam', 'message': error.advice, 'code': error.code}
        return {'status': 'ok', 'rows': engine_scores.judge(*sets)}

    def judge_scores(self):
        """Pure arithmetic on two {concern: raw_score} dicts against YouCam's measured wobble. No photo, no network."""
        if self.headers.get('Content-Type') != 'application/json':
            self.reply(415, {'error': 'JSON required'})
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 4096:
                raise ValueError()
            payload = json.loads(self.rfile.read(length))
            pair = [payload.get('before'), payload.get('after')]
            for side in pair:
                if not isinstance(side, dict) or not 0 < len(side) <= 20 or any(
                        isinstance(v, bool) or not isinstance(v, (int, float)) or not 1 <= v <= 100 for v in side.values()):
                    raise ValueError()
        except (ValueError, AttributeError, TypeError):
            self.reply(400, {'error': 'Send before and after as {concern: raw score 1-100}.'})
            return
        rows = engine_scores.judge(*pair)
        if not rows:
            self.reply(400, {'error': 'No shared YouCam concerns to judge.'})
            return
        self.reply(200, {'rows': rows})

    def compare_photos(self):
        """Measure two photos locally and return a comparability verdict. Photos stay in memory; nothing is stored or sent."""
        if self.headers.get('Content-Type') != 'application/json':
            self.reply(415, {'error': 'JSON required'})
            return
        origin = self.headers.get('Origin')
        if origin and origin != 'http://' + self.headers.get('Host', ''):
            self.reply(403, {'error': 'Local page required'})
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 24 * 1024 * 1024:
                raise ValueError()
            payload = json.loads(self.rfile.read(length))
            images = [base64.b64decode(payload.get(k, ''), validate=True) for k in ('before', 'after')]
            if not all(images):
                raise ValueError()
            want_youcam = payload.get('youcam') is True
            if want_youcam and payload.get('consent') is not True:
                raise ValueError()
            types = [payload.get('before_type', 'image/jpeg'), payload.get('after_type', 'image/jpeg')]
        except (ValueError, AttributeError, TypeError, binascii.Error):
            self.reply(400, {'error': 'Send two photos as base64 (before, after).'})
            return
        measure = self.server.measure
        try:
            prints = [measure(data) for data in images]
        except ImportError:
            self.reply(503, {'error': 'Local photo measurement needs the optional packages in requirements-engine.txt.'})
            return
        except ValueError:
            self.reply(400, {'error': 'A photo could not be read. Use a JPEG or PNG.'})
            return
        for name, fp in zip(('first', 'second'), prints):
            if fp is None:
                self.reply(422, {'error': f'No face found in the {name} photo. Face the camera in good light and retake it.'})
                return
        verdict = engine_compare.verdict(*prints)
        youcam = None
        if want_youcam:
            try:
                youcam = self.run_youcam(images, types, verdict['comparable'])
            except Exception:  # transport, validation or service failure: the local verdict is still returned
                youcam = {'status': 'error', 'message': 'YouCam could not be reached or rejected the photo. The local result above still stands; nothing was saved.'}
        self.reply(200, {**verdict, **({'youcam': youcam} if youcam else {}), 'measured': [
            {k: round(v, 3) if isinstance(v, float) else v for k, v in fp.items()
             if k in ('scale', 'yaw', 'roll_deg', 'pitch', 'light_dir', 'left_cheek_L', 'right_cheek_L', 'left_cheek_a', 'right_cheek_a', 'inside_frame')} for fp in prints]})

    def do_POST(self):
        if self.path == '/judge-scores':
            self.judge_scores()
            return
        if self.path == '/compare-photos':
            self.compare_photos()
            return
        if self.path not in ('/analysis/start', '/analysis/poll'):
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
            client = getattr(self.server, 'analysis_client', None)
            if client is None:
                self.reply(503, {'error': 'YouCam analysis is off: start the server with a YouCam key to enable it.'})
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
        except YouCamTaskError as error:
            self.reply(422, {'error': error.advice, 'code': error.code})
        except (ValueError, AttributeError, TypeError, binascii.Error):
            self.reply(400, {'error': 'Invalid request. Check consent, photo format and task.'})
        except Exception:
            self.reply(502, {'error': 'Analysis service unavailable. No result was saved.'})


def make_server(address=('127.0.0.1', 8766), client=None, measure=None):
    server = HTTPServer(address, Handler)
    if measure is None:
        def measure(data):
            from engine import measure as m
            return m.fingerprint_bytes(data)
    server.measure = measure
    import time
    server.sleep = time.sleep
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
