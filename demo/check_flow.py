"""Browser check of the measured flow against the real local app. The measurer is a stand-in that maps
three tiny marker images to numeric fingerprints (no photos, no external calls); the verdict logic
(engine/compare.py) and the page are the real ones."""
import base64, struct, sys, zlib, tempfile
from pathlib import Path
from threading import Thread
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import make_server
from playwright.sync_api import sync_playwright

BASE = {'scale': .34, 'cx': .5, 'cy': .5, 'inside_frame': True, 'roll_deg': 0.0, 'yaw': 0.02, 'pitch': 0.03,
        'left_cheek_L': 56.0, 'right_cheek_L': 55.0, 'left_cheek_a': 15.0, 'right_cheek_a': 15.0, 'light_dir': 0.01}
PRINTS = {b'A': BASE, b'B': {**BASE, 'left_cheek_L': 66.0, 'right_cheek_L': 65.0, 'left_cheek_a': 20.0, 'right_cheek_a': 20.0},
          b'C': {**BASE, 'left_cheek_a': 24.0}}


def png(tag):
    raw = b'\x00' + bytes([tag[0], 0, 0])
    def chunk(t, d): return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')


TAGS = {png(t): t for t in PRINTS}


def measure(data):
    return PRINTS[TAGS[data]]
server = make_server(('127.0.0.1', 0), measure=measure)
Thread(target=server.serve_forever, daemon=True).start()
tmp = Path(tempfile.mkdtemp())
for t in PRINTS:
    (tmp / (t.decode() + '.png')).write_bytes(png(t))
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, chromium_sandbox=False)
        page = browser.new_page(viewport={'width': 1440, 'height': 900})
        page.goto(f'http://127.0.0.1:{server.server_port}/')
        def run(a, b):
            page.set_input_files('#before', str(tmp / (a + '.png'))); page.set_input_files('#after', str(tmp / (b + '.png')))
            page.locator('#go').click(); page.locator('#result h3').wait_for()
            return page.locator('#result').inner_text()
        text = run('A', 'B')
        assert 'Not comparable yet' in text and 'Brightness' in text and 'Same light' not in text and 'same light' in text.lower(), text
        text = run('A', 'A')
        assert 'no left-versus-right redness difference beyond the noise floor' in text, text
        text = run('A', 'C')
        assert 'left cheek redder' in text, text
        page.screenshot(path=str(Path(__file__).parent / 'flow-desktop.png'), full_page=True)
        browser.close()
    print('Measured flow passed: refused for light, no change, left cheek change.')
finally:
    server.shutdown()
