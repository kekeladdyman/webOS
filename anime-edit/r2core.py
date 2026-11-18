"""Core primitives for the v2 renderer: config, easing, grading, clips/mattes, camera warp, 3D planes, text layers."""
import sys, os, math
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
import importlib
tl = importlib.import_module(os.environ.get("TLMOD", "tl2"))
from extract import key as clip_key

ROOT = tl.ROOT
MODE = sys.argv[1] if len(sys.argv) > 1 else "draft"
W, H, FPS = (1920, 1080, 60) if MODE == "final" else (960, 540, 30)
K = W / 1920.0
FONTS = f"{ROOT}/fonts"
# colours are BGR
BONE = (220, 232, 240); GOLD = (1, 179, 245); RED = (45, 24, 224); VIOLET = (255, 60, 122); INK = (26, 20, 24); BLACK = (0, 0, 0)
DEEP = (58, 12, 34)


def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def smooth(u): u = clamp(u); return u * u * (3 - 2 * u)
def out_cubic(u): u = clamp(u); return 1 - (1 - u) ** 3
def out_expo(u): u = clamp(u); return 1.0 if u >= 1 else 1 - 2 ** (-10 * u)
def in_expo(u): u = clamp(u); return 0.0 if u <= 0 else 2 ** (10 * (u - 1))
def out_back(u, s=1.70158): u = clamp(u); u -= 1; return u * u * ((s + 1) * u + s) + 1
def lerp(a, b, u): return a + (b - a) * u
def noise1(t, seed): return (math.sin(t * 37.1 + seed * 12.9) + 0.6 * math.sin(t * 71.7 + seed * 4.1) + 0.4 * math.sin(t * 113.3 + seed * 7.7)) / 2.0
def slow(t, seed): return (math.sin(t * 1.3 + seed * 3.1) + 0.5 * math.sin(t * 2.9 + seed * 1.7)) / 1.5
def hrand(*k):
    x = math.sin(sum((i + 1) * 127.1 * float(v) for i, v in enumerate(k))) * 43758.5453
    return x - math.floor(x)


# ------------------------------------------------------------------ grading
def make_grade(contrast=1.0, pivot=0.45, lift=(0, 0, 0), gain=(1, 1, 1), gamma=1.0, sat=1.0):
    x = np.arange(256, dtype=np.float32) / 255.0
    lut = np.zeros((256, 1, 3), np.uint8)
    for c in range(3):
        y = np.power(x, gamma); y = (y - pivot) * contrast + pivot
        y = y * gain[c] + lift[c] / 255.0 * (1 - y)
        lut[:, 0, c] = np.clip(y * 255.0 + 0.5, 0, 255).astype(np.uint8)
    return lut, sat


GRADES = {
    "raw": make_grade(),
    "bar_hi": make_grade(contrast=1.18, pivot=0.40, lift=(16, 6, 8), gain=(1.08, 1.02, 1.02), gamma=0.60, sat=1.20),
    "bar": make_grade(contrast=1.16, pivot=0.40, lift=(14, 4, 6), gain=(1.06, 1.0, 1.0), gamma=0.72, sat=1.22),
    "past": make_grade(contrast=1.04, lift=(8, 9, 12), gain=(0.90, 0.97, 1.02), sat=0.72),
    "battle": make_grade(contrast=1.13, lift=(9, 2, 4), gain=(1.02, 1.0, 1.0), sat=1.15),
    "night": make_grade(contrast=1.14, lift=(8, 2, 3), gain=(1.04, 1.02, 1.02), gamma=0.88, sat=1.18),
    "city": make_grade(contrast=1.07, lift=(8, 5, 2), gain=(0.98, 1.0, 1.03), sat=0.92),
}


def apply_grade(img, name):
    lut, sat = GRADES[name]
    img = cv2.LUT(img, lut)
    if abs(sat - 1.0) > 1e-3:
        g = cv2.cvtColor(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
        img = cv2.addWeighted(img, sat, g, 1 - sat, 0)
    return img


# ------------------------------------------------------------------ clips + mattes
class Clips:
    def __init__(self): self.c = {}; self.order = []; self.m = {}
    def get(self, shot):
        k = clip_key(shot)
        if k not in self.c:
            cap = cv2.VideoCapture(f"{ROOT}/cache/{k}.mp4"); fr = []
            while True:
                ok, f = cap.read()
                if not ok: break
                if MODE != "final": f = cv2.resize(f, (W, H), interpolation=cv2.INTER_AREA)
                fr.append(f)
            cap.release(); self.c[k] = fr; self.order.append(k)
            while len(self.order) > 7: self.c.pop(self.order.pop(0), None)
        return self.c[k]
    def matte(self, shot):
        k = clip_key(shot)
        if k not in self.m:
            p = f"{ROOT}/mattes/{k}.npz"
            if not os.path.exists(p): self.m[k] = None
            else:
                m = np.load(p)["m"]
                if MODE != "final": m = np.stack([cv2.resize(x, (W, H), interpolation=cv2.INTER_AREA) for x in m])
                self.m[k] = m
        return self.m[k]


CLIPS = Clips()


def src_time(shot, dt):
    sp = shot["speed"]
    if isinstance(sp, (int, float)): return dt * sp
    d = shot["t1"] - shot["t0"]; n = 40; acc = 0.0; u1 = clamp(dt / d)
    for i in range(n):
        ua = u1 * i / n; ub = u1 * (i + 1) / n; um = (ua + ub) / 2; v = sp[-1][1]
        for (p0, v0), (p1, v1) in zip(sp, sp[1:]):
            if p0 <= um <= p1: v = lerp(v0, v1, (um - p0) / max(1e-6, p1 - p0)); break
        acc += v * (ub - ua) * d
    return acc


def warp(frame, zoom, cx, cy, rot, dx, dy, ow, oh, interp=None):
    sh, sw = frame.shape[:2]
    s = zoom * max(ow / sw, oh / sh)                     # cover-fit
    lim = 0.5 * (1 - 1 / max(zoom, 1.0001))
    cx = clamp(cx, 0.5 - lim, 0.5 + lim); cy = clamp(cy, 0.5 - lim, 0.5 + lim)
    M = cv2.getRotationMatrix2D((cx * sw, cy * sh), rot, s)
    M[0, 2] += ow / 2 - cx * sw + dx; M[1, 2] += oh / 2 - cy * sh + dy
    if interp is None: interp = cv2.INTER_CUBIC if s > 1.02 else (cv2.INTER_AREA if s < 0.75 else cv2.INTER_LINEAR)
    return cv2.warpAffine(frame, M, (ow, oh), flags=interp, borderMode=cv2.BORDER_REFLECT_101)


ZERO_ACC = dict(zoom=0.0, shake=0.0, rgb=0.0, glow=0.0, flash=0.0)


def accents(t):
    a = dict(zoom=0.0, shake=0.0, rgb=0.0, glow=0.0, flash=0.0)
    for s in tl.SHOTS:
        p = s["punch"]
        if p <= 0: continue
        dt = t - s["t0"]
        if 0 <= dt < 0.6:
            a["zoom"] += 0.085 * p * math.exp(-dt / 0.085)
            a["shake"] += 15.0 * p * math.exp(-dt / 0.13)
            a["rgb"] += 3.2 * p * math.exp(-dt / 0.14)
            a["glow"] += 0.55 * p * math.exp(-dt / 0.16)
            a["flash"] += 0.16 * p * math.exp(-dt / 0.05)
    if 8.22 <= t < 15.3 or 25.8 <= t < 28.5 or tl.CHORUS <= t < 33.3:
        for b in tl.B:
            dt = t - b
            if 0 <= dt < 0.3: a["zoom"] += 0.012 * math.exp(-dt / 0.07)
    return a


def render_shot(shot, t, acc=ZERO_ACC, size=None, want_matte=False, zmul=1.0, t_clamp=True, raw=False):
    """returns graded BGR frame (and the matching matte if want_matte) at `size` (default full frame)."""
    ow, oh = size or (W, H)
    fr = CLIPS.get(shot)
    d = shot["t1"] - shot["t0"]; dt = t - shot["t0"]
    if t_clamp: dt = clamp(dt, 0.0, d)
    u = clamp(dt / d)
    st_ = src_time(shot, d - dt) if shot.get("rev") else src_time(shot, dt)
    fi = max(0, min(len(fr) - 1, int(st_ * tl.SRC_FPS + 1e-4)))
    ue = out_cubic(u) * 0.6 + u * 0.4 if shot["punch"] > 0 else u
    zoom = lerp(shot["z"][0], shot["z"][1], ue) * (1 + acc["zoom"]) * zmul
    (x0, y0), (x1, y1) = shot["pan"]
    cx, cy = lerp(x0, x1, ue), lerp(y0, y1, ue)
    rot = lerp(shot["rot"][0], shot["rot"][1], ue)
    amp = (acc["shake"] + shot["shake"] * 5.0) * K * (ow / W)
    dx = amp * noise1(t, 1.0 + shot["id"]); dy = amp * noise1(t, 5.0 + shot["id"]) * 0.8
    rot += amp * 0.012 * noise1(t, 9.0)
    if amp > 0.5: zoom = max(zoom, 1.0 + 2.4 * amp / ow + 0.004)
    zoom = max(zoom, 1.0)
    img = apply_grade(warp(fr[fi], zoom, cx, cy, rot, dx, dy, ow, oh), shot["grade"])
    if shot.get("ink") and not raw: img = ink(img, shot["ink"], shot.get("ink_pct", 58))
    if shot["impact"] and 0 <= t - shot["t0"] < 3.2 / 60.0 and size is None:
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY); thr = float(np.percentile(g[::8, ::8], 62)); m = g > thr
        flip = int((t - shot["t0"]) * 60) % 2 == 0
        out = np.empty_like(img); out[:] = DEEP if flip else BONE; out[m] = BONE if flip else DEEP; img = out
    if not want_matte: return img
    ms = CLIPS.matte(shot)
    if ms is None: return img, None
    m = warp(ms[min(fi, len(ms) - 1)], zoom, cx, cy, rot, dx, dy, ow, oh, interp=cv2.INTER_LINEAR)
    return img, m


# ------------------------------------------------------------------ compositing
def comp_pm(canvas, pm, a, opacity=1.0, x=0, y=0):
    """premultiplied layer (pm,a) over canvas at offset (x,y); clips to canvas."""
    h, w = a.shape[:2]; ch, cw = canvas.shape[:2]
    xa, ya = max(0, x), max(0, y); xb, yb = min(cw, x + w), min(ch, y + h)
    if xa >= xb or ya >= yb or opacity <= 0.003: return
    pm = pm[ya - y:yb - y, xa - x:xb - x]; a = a[ya - y:yb - y, xa - x:xb - x]
    if opacity < 0.999: pm = cv2.convertScaleAbs(pm, alpha=opacity); a = cv2.convertScaleAbs(a, alpha=opacity)
    roi = canvas[ya:yb, xa:xb]
    inv = cv2.merge([255 - a] * 3)
    cv2.multiply(roi, inv, dst=roi, scale=1 / 255.0); cv2.add(roi, pm, dst=roi)


def comp_matte(canvas, img, m):
    """paste img where matte m (uint8) is set (non-premultiplied source)."""
    a3 = cv2.merge([m] * 3)
    fg = cv2.multiply(img, a3, scale=1 / 255.0)             # computed first: img may alias canvas
    cv2.multiply(canvas, 255 - a3, dst=canvas, scale=1 / 255.0)
    cv2.add(canvas, fg, dst=canvas)


def premult(bgr, a):
    return cv2.multiply(bgr, cv2.merge([a] * 3), scale=1 / 255.0)


def Rmat(yaw, pitch, roll):
    y, p, r = math.radians(yaw), math.radians(pitch), math.radians(roll)
    Ry = np.array([[math.cos(y), 0, math.sin(y)], [0, 1, 0], [-math.sin(y), 0, math.cos(y)]])
    Rx = np.array([[1, 0, 0], [0, math.cos(p), -math.sin(p)], [0, math.sin(p), math.cos(p)]])
    Rz = np.array([[math.cos(r), -math.sin(r), 0], [math.sin(r), math.cos(r), 0], [0, 0, 1]])
    return Ry @ Rx @ Rz


def quad3d(w, h, cx, cy, dz=0.0, R=None, scale=1.0, cam=1.0, local_roll=0.0, Rl=None, screen=False):
    """screen quad of a w x h plane centred at screen (cx,cy), depth offset dz (negative = nearer), whole scene rotated by R about
    the screen centre. cam = global zoom."""
    f = 1.7 * W
    c = np.array([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]], np.float64) * scale
    if local_roll:
        a = math.radians(local_roll); rr = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]]); c = c @ rr.T
    loc = np.column_stack([c[:, 0], c[:, 1], np.zeros(4)])
    if Rl is not None: loc = loc @ Rl.T                       # rotate about the plane's own centre
    k = (f + dz) / f if screen else 1.0                       # screen=True: (cx,cy) is where the centre lands on screen
    pts = loc + np.array([(cx - W / 2) * k, (cy - H / 2) * k, float(dz)])
    if R is not None: pts = pts @ R.T
    z = f + pts[:, 2]
    return np.column_stack([W / 2 + cam * f * pts[:, 0] / z, H / 2 + cam * f * pts[:, 1] / z]).astype(np.float32)


def draw_plane(canvas, pm, a, quad, opacity=1.0, interp=cv2.INTER_LINEAR):
    """project premultiplied texture (pm,a) onto canvas at screen quad (4x2: tl,tr,br,bl)."""
    h, w = a.shape[:2]
    src = np.array([[0, 0], [w, 0], [w, h], [0, h]], np.float32)
    x0 = int(max(0, math.floor(quad[:, 0].min()) - 2)); y0 = int(max(0, math.floor(quad[:, 1].min()) - 2))
    x1 = int(min(canvas.shape[1], math.ceil(quad[:, 0].max()) + 2)); y1 = int(min(canvas.shape[0], math.ceil(quad[:, 1].max()) + 2))
    if x1 - x0 < 2 or y1 - y0 < 2: return
    q = quad - np.array([x0, y0], np.float32)
    M = cv2.getPerspectiveTransform(src, q)
    wpm = cv2.warpPerspective(pm, M, (x1 - x0, y1 - y0), flags=interp, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    wa = cv2.warpPerspective(a, M, (x1 - x0, y1 - y0), flags=interp, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    comp_pm(canvas, wpm, wa, opacity, x0, y0)


def put(canvas, pm, a, cx, cy, scale=1.0, rot=0.0, opacity=1.0, sx=None, sy=None):
    """affine-place a premultiplied layer centred at (cx,cy)."""
    h, w = a.shape[:2]; sx = sx or scale; sy = sy or scale
    if abs(rot) < 1e-3 and abs(sx - 1) < 1e-3 and abs(sy - 1) < 1e-3:
        comp_pm(canvas, pm, a, opacity, int(round(cx - w / 2)), int(round(cy - h / 2))); return
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    cs = np.array([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]]) * [sx, sy]
    q = np.column_stack([cx + cs[:, 0] * c - cs[:, 1] * s, cy + cs[:, 0] * s + cs[:, 1] * c]).astype(np.float32)
    draw_plane(canvas, pm, a, q, opacity, interp=cv2.INTER_AREA if max(sx, sy) < 0.7 else cv2.INTER_LINEAR)


# ------------------------------------------------------------------ text
_fc = {}
AXES = {"Fraunces.ttf": lambda w: [144, w, 100, 1], "FrauncesItalic.ttf": lambda w: [144, w, 100, 1],
        "BodoniModa.ttf": lambda w: [w, 96], "BodoniModaItalic.ttf": lambda w: [w, 96]}


def font(name, size, wght=None):
    k = (name, int(round(size)), wght)
    if k not in _fc:
        f = ImageFont.truetype(f"{FONTS}/{name}", int(round(size)))
        if wght is not None:
            try: f.set_variation_by_axes(list(wght) if isinstance(wght, (tuple, list)) else AXES.get(name, lambda w: [w])(wght))
            except Exception: pass
        _fc[k] = f
    return _fc[k]


def tmask(text, fname, size, tracking=0.0, wght=None, vcrop=True, pad=10, vertical=False, line_gap=0.0):
    """alpha mask of text. vertical=True stacks characters top-to-bottom (for kanji)."""
    f = font(fname, size, wght); asc, desc = f.getmetrics()
    if vertical:
        cw = max(f.getlength(ch) for ch in text); chh = asc + desc + line_gap
        im = Image.new("L", (int(cw + 2 * pad), int(chh * len(text) + 2 * pad)), 0); dr = ImageDraw.Draw(im)
        for i, ch in enumerate(text): dr.text((pad + (cw - f.getlength(ch)) / 2, pad + i * chh), ch, font=f, fill=255)
    else:
        ws = [f.getlength(ch) for ch in text]
        im = Image.new("L", (max(4, int(sum(ws) + tracking * (len(text) - 1) + 2 * pad + size * 0.3)), int(asc + desc + 2 * pad + size * 0.2)), 0)
        dr = ImageDraw.Draw(im); x = pad + size * 0.1
        for ch, cw in zip(text, ws): dr.text((x, pad), ch, font=f, fill=255); x += cw + tracking
    a = np.array(im); ys, xs = np.where(a > 8)
    if len(ys):
        if vcrop: a = a[max(0, ys.min() - 3):ys.max() + 4, max(0, xs.min() - 3):xs.max() + 4]
        else: a = a[:, max(0, xs.min() - 3):xs.max() + 4]
    return a


def letters(text, fname, size, tracking=0.0, wght=None):
    """per-letter masks sharing a baseline: list of (mask, x_left) and total (w,h)."""
    f = font(fname, size, wght); asc, desc = f.getmetrics(); pad = int(size * 0.15) + 6
    out = []; x = 0.0; hh = int(asc + desc + 2 * pad)
    for ch in text:
        cw = f.getlength(ch)
        if ch != " ":
            im = Image.new("L", (int(cw + 2 * pad), hh), 0); ImageDraw.Draw(im).text((pad, pad), ch, font=f, fill=255)
            out.append((np.array(im), x - pad))
        x += cw + tracking
    return out, (x - tracking, hh)


def layer(mask, fill=BONE, grad=None, stroke=None, extrude=None, glow=None, shadow=None):
    """style an alpha mask -> premultiplied (pm, a). grad=(top,bottom) | stroke=(color,px) | extrude=(n,dx,dy,color) |
    glow=(color,sigma,gain) | shadow=(sigma,opacity,dx,dy)"""
    padx = pady = 0
    if stroke: padx = pady = int(stroke[1]) + 2
    if extrude: padx += abs(int(extrude[0] * extrude[1])) + 2; pady += abs(int(extrude[0] * extrude[2])) + 2
    if glow: padx += int(glow[1] * 3); pady += int(glow[1] * 3)
    if shadow: padx += int(shadow[0] * 3 + abs(shadow[2])); pady += int(shadow[0] * 3 + abs(shadow[3]))
    m = cv2.copyMakeBorder(mask, pady, pady, padx, padx, cv2.BORDER_CONSTANT, value=0)
    h, w = m.shape
    col = np.zeros((h, w, 3), np.float32); alp = np.zeros((h, w), np.float32)
    def over(c, a):                      # layer (colour c [h,w,3] or tuple, alpha a float 0..1) OVER current
        nonlocal col, alp
        c = np.asarray(c, np.float32)
        if c.ndim == 1: c = np.broadcast_to(c, (h, w, 3))
        col = c * a[..., None] + col * (1 - a[..., None]); alp = a + alp * (1 - a)
    mf = m.astype(np.float32) / 255.0
    if shadow:
        sm = cv2.GaussianBlur(mf, (0, 0), shadow[0]); sm = np.roll(np.roll(sm, int(shadow[3]), 0), int(shadow[2]), 1)
        over((0, 0, 0), sm * shadow[1])
    if glow:
        g = np.clip(cv2.GaussianBlur(mf, (0, 0), glow[1]) * glow[2], 0, 1); over(glow[0], g)
    if extrude:
        n, dx, dy, ec = extrude; e = np.zeros_like(mf)
        for i in range(int(n), 0, -1): e = np.maximum(e, np.roll(np.roll(mf, int(round(i * dy)), 0), int(round(i * dx)), 1))
        over(ec, e)
    if stroke:
        k = int(stroke[1]) * 2 + 1
        over(stroke[0], cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))).astype(np.float32) / 255.0)
    if grad:
        ys = np.where(m.max(1) > 8)[0]; y0, y1 = (ys.min(), ys.max()) if len(ys) else (0, h - 1)
        u = np.clip((np.arange(h) - y0) / max(1, y1 - y0), 0, 1)[:, None, None]
        over(np.asarray(grad[0], np.float32) * (1 - u) + np.asarray(grad[1], np.float32) * u + np.zeros((h, w, 3), np.float32), mf)
    else:
        over(fill, mf)
    a8 = np.clip(alp * 255 + 0.5, 0, 255).astype(np.uint8)
    pm = np.clip(col * alp[..., None] + 0.5, 0, 255).astype(np.uint8)
    return pm, a8


def outline(mask, px):
    k = max(3, int(round(px))) | 1
    return cv2.morphologyEx(mask, cv2.MORPH_GRADIENT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))


# ------------------------------------------------------------------ V4: ink treatment + circle transitions
INK_PAL = {"wb": ((244, 246, 248), (10, 8, 10)), "bw": ((14, 10, 12), (240, 243, 246)), "red": ((12, 6, 10), (45, 24, 224))}
_clahe = cv2.createCLAHE(clipLimit=2.6, tileGridSize=(4, 4))


def ink(img, pal="wb", pct=58, glow=1.0, lines=True):
    """two-tone ink look (like the show's logo art). bright -> fg, dark -> bg; line art kept; saturated light (eyes, magic) keeps its colour."""
    fg, bg = INK_PAL[pal]; k_ = img.shape[1] / 1920.0
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cl = cv2.bilateralFilter(_clahe.apply(g), 7, 40, 5)
    thr = float(cv2.threshold(cl[::4, ::4], 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[0]) if pct == "otsu" else float(np.percentile(cl[::6, ::6], pct))
    m = np.clip((cl.astype(np.float32) - thr) / (9.0 * max(0.6, k_)) + 0.5, 0, 1)
    if lines:                                           # dark outlines inside lit areas survive as ink lines
        dl = cv2.subtract(cv2.GaussianBlur(g, (0, 0), max(1.2, 3.0 * k_)), g).astype(np.float32)
        m *= 1.0 - np.clip((dl - 9.0) / 8.0, 0, 1)
    out = np.asarray(fg, np.float32) * m[..., None] + np.asarray(bg, np.float32) * (1 - m[..., None])
    if glow > 0:
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        k = np.clip((hsv[..., 1].astype(np.float32) - 95) / 50, 0, 1) * np.clip((hsv[..., 2].astype(np.float32) - 105) / 60, 0, 1)
        k = (cv2.GaussianBlur(k, (0, 0), max(1.0, 2.0 * k_)) * glow)[..., None]
        out = out * (1 - k) + np.clip(img.astype(np.float32) * 1.45, 0, 255) * k
    return np.clip(out, 0, 255).astype(np.uint8)


def zoom_at(img, s, px, py, qx=None, qy=None, reflect=False):
    """scale by s about source point (px,py) and place that point at (qx,qy)."""
    qx = px if qx is None else qx; qy = py if qy is None else qy
    M = np.float32([[s, 0, qx - s * px], [0, s, qy - s * py]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR if s >= 0.75 else cv2.INTER_AREA,
                          borderMode=cv2.BORDER_REFLECT_101 if reflect else cv2.BORDER_CONSTANT, borderValue=0)


def circ_mask(cx, cy, r, feather=None):
    m = np.zeros((H, W), np.uint8)
    if r > 0.5: cv2.circle(m, (int(round(cx)), int(round(cy))), int(round(r)), 255, -1, cv2.LINE_AA)
    f = (3.0 * K if feather is None else feather)
    return cv2.GaussianBlur(m, (0, 0), f) if f > 0.4 else m


def iris_through(A_, B_, cx, cy, u, ring=(255, 255, 255), s_end=9.0):
    """camera dives into the point (cx,cy) of A_ while B_ opens inside a growing circle there."""
    sA = s_end ** (u ** 1.5); qx = lerp(cx, W / 2, smooth(u)); qy = lerp(cy, H / 2, smooth(u))
    canvas = zoom_at(A_, sA, cx, cy, qx, qy, reflect=True)
    R = 1.25 * math.hypot(W, H) / 2 * (u ** 2.2)
    if R > 1:
        comp_matte(canvas, zoom_at(B_, lerp(1.28, 1.0, out_cubic(u)), W / 2, H / 2), circ_mask(qx, qy, R))
        if u < 0.92: cv2.circle(canvas, (int(qx), int(qy)), int(R), ring, max(1, int(5 * K * (1 - u))), cv2.LINE_AA)
    return canvas


def circle_match(A_, B_, ca, cb, u, close=0.34, ring=(235, 240, 255)):
    """A_'s circle ca=(x,y,r) is isolated by a closing iris, then shrinks and lands exactly on B_'s circle cb while B_ pulls back around it."""
    if u < close:
        k = smooth(u / close); x, y, r = ca
        canvas = zoom_at(B_, r / cb[2], cb[0], cb[1], x, y, reflect=True)
        rf = max(math.hypot(x - px, y - py) for px in (0, W) for py in (0, H)) + 8
        comp_matte(canvas, A_, circ_mask(x, y, lerp(rf, r, k)))
        return canvas
    v = (u - close) / (1 - close); e = smooth(v)
    x = lerp(ca[0], cb[0], e); y = lerp(ca[1], cb[1], e); r = ca[2] * (cb[2] / ca[2]) ** e
    canvas = zoom_at(B_, r / cb[2], cb[0], cb[1], x, y, reflect=True)
    fade = 1.0 - smooth((v - 0.62) / 0.38)
    m = circ_mask(x, y, r, feather=1.5 * K)
    comp_matte(canvas, zoom_at(A_, r / ca[2], ca[0], ca[1], x, y), cv2.convertScaleAbs(m, alpha=fade) if fade < 0.999 else m)
    if fade > 0.05: cv2.circle(canvas, (int(x), int(y)), int(r), tuple(int(c_ * fade) for c_ in ring), max(1, int(3 * K)), cv2.LINE_AA)
    return canvas
