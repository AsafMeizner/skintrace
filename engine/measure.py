"""Capture fingerprint from pixels only (local MediaPipe FaceMesh, no network, no vendor API).

Per photo: face scale and position, head roll/yaw/pitch proxies from landmarks, skin colour
(CIE L*a*b* medians) of left cheek, right cheek and forehead polygons, light direction (left vs
right cheek brightness), and sharpness of the normalised face crop.
"""
import cv2
import numpy as np


ZONES = {
    'left_cheek': [50, 101, 118, 117, 116, 123, 187, 205],
    'right_cheek': [280, 330, 347, 346, 345, 352, 411, 425],
    'forehead': [103, 67, 109, 10, 338, 297, 332, 151, 108, 9],
}



_MESH = None


def mesh():
    global _MESH
    if _MESH is None:
        import mediapipe as mp  # optional, heavy: imported only when a photo is measured
        _MESH = mp.solutions.face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1, refine_landmarks=False,
                                                min_detection_confidence=0.3)
    return _MESH


def decode(data, width=1200):
    """Bytes of a JPEG/PNG -> BGR image, in memory only."""
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError('unreadable image')
    h, w = img.shape[:2]
    return cv2.resize(img, (width, int(h * width / w)), interpolation=cv2.INTER_AREA)


def fingerprint_bytes(data):
    img = decode(data)
    pts = landmarks(img)
    return None if pts is None else fingerprint_img(img, pts)


def load(path, width=1200):
    img = cv2.imread(path)
    if img is None:
        raise ValueError('unreadable image')
    h, w = img.shape[:2]
    return cv2.resize(img, (width, int(h * width / w)), interpolation=cv2.INTER_AREA)


def landmarks(img):
    res = mesh().process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    if not res.multi_face_landmarks:
        return None
    h, w = img.shape[:2]
    return np.array([(p.x * w, p.y * h) for p in res.multi_face_landmarks[0].landmark], dtype=np.float32)


def zone_stats(lab, pts, idx):
    mask = np.zeros(lab.shape[:2], np.uint8)
    cv2.fillConvexPoly(mask, cv2.convexHull(pts[idx].astype(np.int32)), 1)
    vals = lab[mask.astype(bool)]
    if len(vals) < 50:
        return None
    return np.median(vals, axis=0)


def fingerprint(path, inject=None):
    """inject = (zone_name, delta_a): add delta_a to a* inside that zone before measuring (synthetic validation only)."""
    img = load(path)
    pts = landmarks(img)
    if pts is None:
        return None
    return fingerprint_img(img, pts, inject)


def fingerprint_img(img, pts, inject=None):
    H, W = img.shape[:2]
    lab = cv2.cvtColor(img.astype(np.float32) / 255.0, cv2.COLOR_BGR2LAB)  # float L*a*b*: L 0..100, a/b about -128..127
    if inject:
        zone, delta = inject
        m = np.zeros(lab.shape[:2], np.float32)
        cv2.fillConvexPoly(m, cv2.convexHull(pts[ZONES[zone]].astype(np.int32)), 1.0)
        lab[..., 1] += delta * cv2.GaussianBlur(m, (0, 0), 6)
    xs, ys = pts[:, 0], pts[:, 1]
    fw = float(np.linalg.norm(pts[454] - pts[234]))
    out = {'scale': fw / W, 'cx': float(xs.mean() / W), 'cy': float(ys.mean() / H),
           'inside_frame': bool(xs.min() >= 0 and xs.max() < W and ys.min() >= 0 and ys.max() < H)}
    eye_l, eye_r = pts[33], pts[263]
    out['roll_deg'] = float(np.degrees(np.arctan2(eye_r[1] - eye_l[1], eye_r[0] - eye_l[0])))
    out['yaw'] = float((pts[1][0] - (pts[234][0] + pts[454][0]) / 2) / fw)
    out['pitch'] = float((pts[1][1] - (pts[10][1] + pts[152][1]) / 2) / max(float(np.linalg.norm(pts[152] - pts[10])), 1))
    for name, idx in ZONES.items():
        s = zone_stats(lab, pts, idx)
        if s is None:
            return None
        out[name + '_L'], out[name + '_a'], out[name + '_b'] = (float(v) for v in s)
    L, R = out['left_cheek_L'], out['right_cheek_L']
    out['light_dir'] = (L - R) / (L + R)
    x0, x1, y0, y1 = [int(v) for v in (max(xs.min(), 0), min(xs.max(), W - 1), max(ys.min(), 0), min(ys.max(), H - 1))]
    face = cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
    face = cv2.resize(face, (256, max(int(256 * face.shape[0] / max(face.shape[1], 1)), 1)), interpolation=cv2.INTER_AREA)
    out['sharpness'] = float(cv2.Laplacian(face, cv2.CV_64F).var())
    return out
