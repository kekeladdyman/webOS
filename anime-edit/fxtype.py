"""Display type with real treatments (3D bevel/extrude, brushed metal, chrome, glow, VRENS stacks).
All functions return (premultiplied BGR uint8, alpha uint8) layers, compatible with r2core.put / comp_pm."""
import math, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

FD = __import__("os").path.dirname(__import__("os").path.abspath(__file__)) + "/fonts2/"
_fc = {}


def font(name, size, var=None):
    k = (name, int(size), tuple(var) if var else None)
    if k not in _fc:
        p = name if "/" in name else (FD + name if __import__("os").path.exists(FD + name) else FD + "../fonts/" + name)
        f = ImageFont.truetype(p, int(size))
        if var:
            try: f.set_variation_by_axes(list(var))
            except Exception: pass
        _fc[k] = f
    return _fc[k]


def glyphs(text, name, size, tracking=0.0, var=None, pad=None):
    """tight alpha mask of a line of text."""
    f = font(name, size, var); asc, desc = f.getmetrics(); pad = int(size * 0.25) if pad is None else pad
    ws = [f.getlength(c) for c in text]
    im = Image.new("L", (int(sum(ws) + tracking * max(0, len(text) - 1) + 2 * pad + size * 0.4), int(asc + desc + 2 * pad)), 0)
    d = ImageDraw.Draw(im); x = pad
    for c, w in zip(text, ws): d.text((x, pad), c, font=f, fill=255); x += w + tracking
    a = np.array(im); ys, xs = np.where(a > 8)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1] if len(ys) else a


def stack(lines, gap=0.06, align="left"):
    """stack masks vertically. lines = list of masks."""
    w = max(m.shape[1] for m in lines); g = int(max(m.shape[0] for m in lines) * gap)
    h = sum(m.shape[0] for m in lines) + g * (len(lines) - 1); out = np.zeros((h, w), np.uint8); y = 0
    for m in lines:
        x = 0 if align == "left" else (w - m.shape[1]) // 2 if align == "center" else w - m.shape[1]
        out[y:y + m.shape[0], x:x + m.shape[1]] = m; y += m.shape[0] + g
    return out


def shear(mask, k=0.2):
    h, w = mask.shape; return cv2.warpAffine(mask, np.float32([[1, -k, k * h], [0, 1, 0]]), (w + int(abs(k) * h) + 2, h))


def _pad(m, p): return cv2.copyMakeBorder(m, p, p, p, p, cv2.BORDER_CONSTANT, value=0)


def _lin(c): return np.asarray(c, np.float32)


class Comp:
    """small premultiplied compositor (float32, 0..1)."""
    def __init__(self, h, w): self.c = np.zeros((h, w, 3), np.float32); self.a = np.zeros((h, w), np.float32)
    def over(self, col, a):
        col = np.asarray(col, np.float32)
        if col.ndim == 1: col = np.broadcast_to(col / 255.0, self.c.shape)
        elif col.max() > 1.5: col = col / 255.0
        self.c = col * a[..., None] + self.c * (1 - a[..., None]); self.a = a + self.a * (1 - a)
    def layer(self):
        return np.clip(self.c * self.a[..., None] * 255 + 0.5, 0, 255).astype(np.uint8), np.clip(self.a * 255 + 0.5, 0, 255).astype(np.uint8)


def _bevel(m, bw, light=(-0.6, -0.8)):
    """shading -1..1 from a bevel of width bw on mask m (0..1)."""
    dt = cv2.distanceTransform((m > 0.5).astype(np.uint8), cv2.DIST_L2, 5)
    h = np.clip(dt / max(1.0, bw), 0, 1); h = 1 - (1 - h) ** 2
    h = cv2.GaussianBlur(h, (0, 0), max(0.6, bw * 0.15))
    gx = cv2.Sobel(h, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(h, cv2.CV_32F, 0, 1, ksize=3)
    n = np.sqrt(gx * gx + gy * gy + 1e-6); lx, ly = light; s = -(gx * lx + gy * ly) / (n + 0.25)
    return np.clip(s * 1.4, -1, 1), h


def metal3d(mask, top=(235, 240, 245), bot=(120, 125, 130), depth=0.10, angle=35, ext=(40, 40, 46), ext_far=(8, 8, 10),
            glow=None, spec=0.55, bevel=0.06, rim=(255, 255, 255), noise=0.0, shadow=0.55):
    """extruded, bevelled letters lit from the top-left (JPOXI HIDEOUS / WAIT / GUY)."""
    h0 = mask.shape[0]; D = max(2, int(h0 * depth)); dx, dy = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    gpad = int(glow[1] * 3) if glow else 0; P = D + gpad + int(h0 * 0.08) + 4
    m = _pad(mask, P).astype(np.float32) / 255.0; Hh, Ww = m.shape; C = Comp(Hh, Ww)
    if shadow:
        sm = cv2.GaussianBlur(m, (0, 0), h0 * 0.05); sm = np.roll(np.roll(sm, int(D * dy * 1.6), 0), int(D * dx * 1.6), 1); C.over((0, 0, 0), sm * shadow)
    if glow:
        g = np.clip(cv2.GaussianBlur(m, (0, 0), glow[1]) * glow[2], 0, 1); C.over(glow[0], g)
    for i in range(D, 0, -1):                                    # extrusion, darker further back
        u = i / D; col = _lin(ext) * (1 - u) + _lin(ext_far) * u
        C.over(col, np.roll(np.roll(m, int(round(i * dy)), 0), int(round(i * dx)), 1))
    s, hb = _bevel(m, h0 * bevel)
    yy = np.linspace(0, 1, Hh, dtype=np.float32)[:, None, None]
    ys = np.where(m.max(1) > 0.5)[0]; y0, y1 = (ys.min(), ys.max()) if len(ys) else (0, Hh - 1)
    v = np.clip((np.arange(Hh) - y0) / max(1, y1 - y0), 0, 1).astype(np.float32)[:, None, None]
    face = _lin(top) * (1 - v) + _lin(bot) * v
    face = face * (0.82 + 0.30 * s[..., None])
    band = np.exp(-((v[..., 0] - 0.36) / 0.10) ** 2)[..., None] * spec * 255        # specular band
    face = face + band * (0.6 + 0.4 * np.clip(s, 0, 1)[..., None])
    if noise: face = face + np.random.default_rng(1).normal(0, noise, face.shape[:2])[..., None]
    C.over(np.clip(face, 0, 255), m)
    edge = np.clip(cv2.morphologyEx(m, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) * np.clip(s, 0, 1) * 1.2, 0, 1)
    C.over(rim, edge * 0.7)
    return C.layer()


def chrome(mask, c1=(60, 200, 230), c2=(250, 255, 255), c3=(40, 120, 170), depth=0.05, angle=40, ext=(20, 60, 90), glow=None):
    """reflective chrome gradient (MASSACRE)."""
    h0 = mask.shape[0]; P = int(h0 * 0.3) + 4; m = _pad(mask, P).astype(np.float32) / 255.0; Hh, Ww = m.shape; C = Comp(Hh, Ww)
    if glow: C.over(glow[0], np.clip(cv2.GaussianBlur(m, (0, 0), glow[1]) * glow[2], 0, 1))
    D = max(1, int(h0 * depth)); dx, dy = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    for i in range(D, 0, -1): C.over(_lin(ext) * (0.5 + 0.5 * (1 - i / D)), np.roll(np.roll(m, int(round(i * dy)), 0), int(round(i * dx)), 1))
    ys = np.where(m.max(1) > 0.5)[0]; y0, y1 = (ys.min(), ys.max()) if len(ys) else (0, Hh - 1)
    v = np.clip((np.arange(Hh) - y0) / max(1, y1 - y0), 0, 1).astype(np.float32)[:, None]
    xx = np.linspace(0, 1, Ww, dtype=np.float32)[None, :]; ph = v + 0.25 * np.sin(xx * 9.0) * 0.3
    k1 = np.clip(1 - np.abs(ph - 0.45) / 0.12, 0, 1); k3 = np.clip((ph - 0.55) / 0.45, 0, 1)
    face = _lin(c1)[None, None] * (1 - k3[..., None]) + _lin(c3)[None, None] * k3[..., None]; face = face * (1 - k1[..., None]) + _lin(c2) * k1[..., None]
    s, _ = _bevel(m, h0 * 0.05); face = face * (0.85 + 0.25 * s[..., None])
    C.over(np.clip(face, 0, 255), m); return C.layer()


def vrens(mask, fill=(250, 250, 250), depth=0.16, angle=50, ext=(12, 10, 12), outline=None, shadow=0.5):
    """flat bright face on a deep hard black extrusion (VRENS stacks)."""
    h0 = mask.shape[0]; D = max(2, int(h0 * depth)); dx, dy = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    P = D + int(h0 * 0.08) + 4; m = _pad(mask, P).astype(np.float32) / 255.0; Hh, Ww = m.shape; C = Comp(Hh, Ww)
    if shadow:
        sm = cv2.GaussianBlur(m, (0, 0), h0 * 0.04); sm = np.roll(np.roll(sm, int(D * dy * 1.3), 0), int(D * dx * 1.3), 1); C.over((0, 0, 0), sm * shadow)
    e = np.zeros_like(m)
    for i in range(D, 0, -1): e = np.maximum(e, np.roll(np.roll(m, int(round(i * dy)), 0), int(round(i * dx)), 1))
    C.over(ext, e)
    if outline: C.over(outline[0], cv2.dilate(m, np.ones((outline[1] * 2 + 1,) * 2, np.uint8)))
    C.over(fill, m); return C.layer()


def flat(mask, fill, glow=None, shadow=None, grad=None):
    h0 = mask.shape[0]; P = int(h0 * 0.25) + (int(glow[1] * 3) if glow else 0) + 4; m = _pad(mask, P).astype(np.float32) / 255.0; Hh, Ww = m.shape; C = Comp(Hh, Ww)
    if shadow:
        sm = cv2.GaussianBlur(m, (0, 0), shadow[0]); sm = np.roll(sm, int(shadow[2]), 0); C.over((0, 0, 0), sm * shadow[1])
    if glow: C.over(glow[0], np.clip(cv2.GaussianBlur(m, (0, 0), glow[1]) * glow[2], 0, 1))
    if grad:
        v = np.linspace(0, 1, Hh, dtype=np.float32)[:, None, None]; C.over(_lin(grad[0]) * (1 - v) + _lin(grad[1]) * v, m)
    else: C.over(fill, m)
    return C.layer()
