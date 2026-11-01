"""RUN ONLY WITH THE OWNER'S WRITTEN YES. Sends face-cropped copies of the 12 window photos to YouCam (SD concerns),
saves YouCam's raw scores per concern (numbers only) to spike/youcam_scores.json. Cap: 400 units. Needs YOUCAM_API_KEY
and the network host yce-us.s3-accelerate.amazonaws.com. Run with /workspace/.venv-skin/bin/python."""
import json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import cv2
from engine.measure import load, landmarks
from youcam import YouCamClient, YouCamTaskError, SD_ACTIONS
from transport import HTTPTransport

SRC = sys.argv[1]
CAP_UNITS, UNITS_PER_PHOTO = 400, 16
names = [f'window-front-{i}.jpg' for i in range(1, 7)] + [f'window-behind-{i}.jpg' for i in range(1, 7)]
client = YouCamClient(os.environ['YOUCAM_API_KEY'], HTTPTransport(timeout=30), allowed_upload_hosts=['yce-us.s3-accelerate.amazonaws.com'])


def crop(path):
    """Face width about 75% of the photo (YouCam needs > 60%), JPEG under 2 MB, in memory only."""
    img = load(path, 2000)
    pts = landmarks(img)
    if pts is None:
        raise ValueError('no face')
    x0, x1 = pts[:, 0].min(), pts[:, 0].max()
    y0, y1 = pts[:, 1].min(), pts[:, 1].max()
    w = (x1 - x0) / 0.75
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    h = w * 4 / 3
    X0, X1 = int(max(cx - w / 2, 0)), int(min(cx + w / 2, img.shape[1]))
    Y0, Y1 = int(max(cy - h / 2, 0)), int(min(cy + h / 2, img.shape[0]))
    out = img[Y0:Y1, X0:X1]
    ok, buf = cv2.imencode('.jpg', out, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return bytes(buf)


results, spent = {}, 0
for n in names:
    if spent + UNITS_PER_PHOTO > CAP_UNITS:
        break
    try:
        task = client.start(crop(os.path.join(SRC, n)), 'image/jpeg', consent=True, actions=list(SD_ACTIONS))
        for _ in range(40):
            time.sleep(2)
            scores = client.poll_once(task)
            if scores is not None:
                results[n] = scores; spent += UNITS_PER_PHOTO; break
        else:
            results[n] = {'error': 'timeout'}
    except YouCamTaskError as e:
        results[n] = {'error': e.code}
    except Exception as e:
        results[n] = {'error': e.__class__.__name__}
    print(n, 'ok' if 'error' not in results[n] else results[n]['error'], flush=True)
json.dump(results, open(os.path.join(os.path.dirname(__file__), 'youcam_scores.json'), 'w'), indent=1)
print('units counted (upper bound):', spent)
