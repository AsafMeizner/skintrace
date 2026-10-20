"""Exercise the recorded flow against the real local app, without external calls."""
import sys
from pathlib import Path
from threading import Thread
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import make_server
from playwright.sync_api import sync_playwright
server = make_server(('127.0.0.1', 0))
Thread(target=server.serve_forever, daemon=True).start()
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, chromium_sandbox=False)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        page.goto(f'http://127.0.0.1:{server.server_port}/')
        page.locator('#submit').click()
        page.get_by_role('heading', name='Pause the comparison').wait_for()
        for name in ('lighting', 'camera', 'pose'):
            page.locator('#'+name).check()
        page.locator('#submit').click()
        page.get_by_role('heading', name='Cosmetic score differences').wait_for()
        assert 'texture: +5 points' in page.locator('#result').inner_text()
        assert 'pore: -2 points' in page.locator('#result').inner_text()
        assert 'Live analysis is currently disabled' in page.locator('#analysis').inner_text()
        browser.close()
    print('Demo flow passed: blocked comparison, confirmed synthetic differences, disabled live disclosure.')
finally:
    server.shutdown()
