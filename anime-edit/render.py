"""Frame renderer for the edit. usage: render.py [draft|final] [t_start t_end] ; writes out/<mode>_video.mp4"""
import sys, os, math, subprocess, multiprocessing as mp
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
import tl
from extract import key as clip_key

ROOT = tl.ROOT
MODE = sys.argv[1] if len(sys.argv) > 1 else "draft"
W, H, FPS = (1920, 1080, 60) if MODE == "final" else (960, 540, 30)
K = W / 1920.0                       # resolution scale for pixel-sized things
T0 = float(sys.argv[2]) if len(sys.argv) > 3 else 0.0
T1 = float(sys.argv[3]) if len(sys.argv) > 3 else tl.END
NW = 4
BONE = (218, 232, 240)               # BGR bone white
FONTS = f"{ROOT}/fonts"


# ------------------------------------------------------------------ helpers
def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def smooth(u): u = clamp(u); return u * u * (3 - 2 * u)
def out_cubic(u): u = clamp(u); return 1 - (1 - u) ** 3
def out_expo(u): u = clamp(u); return 1.0 if u >= 1 else 1 - 2 ** (-10 * u)
def in_expo(u): u = clamp(u); return 0.0 if u <= 0 else 2 ** (10 * (u - 1))
def lerp(a, b, u): return a + (b - a) * u


def noise1(t, seed):
    return (math.sin(t * 37.1 + seed * 12.9) + 0.6 * math.sin(t * 71.7 + seed * 4.1) + 0.4 * math.sin(t * 113.3 + seed * 7.7)) / 2.0


# ------------------------------------------------------------------ grading
def make_grade(contrast=1.0, pivot=0.45, lift=(0, 0, 0), gain=(1, 1, 1), gamma=1.0, sat=1.0):
    x = np.arange(256, dtype=np.float32) / 255.0
    lut = np.zeros((256, 1, 3), np.uint8)
    for c in range(3):  # B,G,R
        y = np.power(x, gamma)
        y = (y - pivot) * contrast + pivot
        y = y * gain[c] + lift[c] / 255.0 * (1 - y)
        lut[:, 0, c] = np.clip(y * 255.0 + 0.5, 0, 255).astype(np.uint8)
    return lut, sat


GRADES = {
    "past": make_grade(contrast=1.02, lift=(10, 9, 12), gain=(0.95, 0.98, 1.0), sat=0.80),
    "battle": make_grade(contrast=1.12, lift=(9, 2, 4), gain=(1.02, 1.0, 1.0), sat=1.14),
    "night": make_grade(contrast=1.14, lift=(8, 2, 3), gain=(1.04, 1.02, 1.02), gamma=0.88, sat=1.18),
    "city": make_grade(contrast=1.06, lift=(8, 5, 2), gain=(0.98, 1.0, 1.03), sat=0.90),
}


def apply_grade(img, name):
    lut, sat = GRADES[name]
    img = cv2.LUT(img, lut)
    if abs(sat - 1.0) > 1e-3:
        g = cv2.cvtColor(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
        img = cv2.addWeighted(img, sat, g, 1 - sat, 0)
    return img


# ------------------------------------------------------------------ clips
class Clips:
    def __init__(self): self.c = {}; self.order = []
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
            while len(self.order) > 5: self.c.pop(self.order.pop(0), None)
        return self.c[k]


CLIPS = Clips()


def src_time(shot, dt):
    sp = shot["speed"]
    if isinstance(sp, (int, float)): return dt * sp
    d = shot["t1"] - shot["t0"]; n = 40; acc = 0.0; u1 = clamp(dt / d)
    for i in range(n):
        ua = u1 * i / n; ub = u1 * (i + 1) / n; um = (ua + ub) / 2
        v = sp[-1][1]
        for (p0, v0), (p1, v1) in zip(sp, sp[1:]):
            if p0 <= um <= p1: v = lerp(v0, v1, (um - p0) / max(1e-6, p1 - p0)); break
        acc += v * (ub - ua) * d
    return acc


def warp(frame, zoom, cx, cy, rot, dx, dy, ow=None, oh=None):
    ow = ow or W; oh = oh or H
    sh, sw = frame.shape[:2]
    s = zoom * (ow / sw)
    lim = 0.5 * (1 - 1 / max(zoom, 1.0001))
    cx = clamp(cx, 0.5 - lim, 0.5 + lim); cy = clamp(cy, 0.5 - lim, 0.5 + lim)
    M = cv2.getRotationMatrix2D((cx * sw, cy * sh), rot, s)
    M[0, 2] += ow / 2 - cx * sw + dx; M[1, 2] += oh / 2 - cy * sh + dy
    return cv2.warpAffine(frame, M, (ow, oh), flags=cv2.INTER_CUBIC if s > 1.02 else cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)


def accents(t):
    """sum of decaying impulses from shot cuts -> dict of amounts"""
    a = dict(zoom=0.0, shake=0.0, rgb=0.0, glow=0.0, flash=0.0)
    for s in tl.SHOTS:
        p = s["punch"]
        if p <= 0 or s["region"]: continue
        dt = t - s["t0"]
        if 0 <= dt < 0.6:
            a["zoom"] += 0.085 * p * math.exp(-dt / 0.085)
            a["shake"] += 15.0 * p * math.exp(-dt / 0.13)
            a["rgb"] += 3.2 * p * math.exp(-dt / 0.14)
            a["glow"] += 0.55 * p * math.exp(-dt / 0.16)
            a["flash"] += 0.16 * p * math.exp(-dt / 0.05)
    # beat bounce inside the rhythmic sections
    if 8.22 <= t < 15.3 or 21.34 <= t < 28.5 or tl.CHORUS <= t < 33.3:
        for b in tl.B:
            dt = t - b
            if 0 <= dt < 0.3: a["zoom"] += 0.012 * math.exp(-dt / 0.07)
    return a


def render_shot(shot, t, acc):
    fr = CLIPS.get(shot)
    dt = t - shot["t0"]; d = shot["t1"] - shot["t0"]; u = clamp(dt / d)
    fi = min(len(fr) - 1, int(src_time(shot, dt) * tl.SRC_FPS + 1e-4))
    ue = out_cubic(u) * 0.6 + u * 0.4 if shot["punch"] > 0 else u
    zoom = lerp(shot["z"][0], shot["z"][1], ue) * (1 + acc["zoom"])
    (x0, y0), (x1, y1) = shot["pan"]
    cx, cy = lerp(x0, x1, ue), lerp(y0, y1, ue)
    rot = lerp(shot["rot"][0], shot["rot"][1], ue)
    amp = (acc["shake"] + shot["shake"] * 5.0) * K
    dx = amp * noise1(t, 1.0 + shot["id"]); dy = amp * noise1(t, 5.0 + shot["id"]) * 0.8
    rot += amp * 0.012 * noise1(t, 9.0)
    if amp > 0.5: zoom = max(zoom, 1.0 + 2.4 * amp / W + 0.004)
    img = warp(fr[fi], max(zoom, 1.0), cx, cy, rot, dx, dy)
    img = apply_grade(img, shot["grade"])
    if shot["impact"] and dt < 3.2 / 60.0:
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY); thr = float(np.percentile(g[::8, ::8], 62))
        m = (g > thr)
        out = np.empty_like(img); out[:] = (58, 12, 34) if int(dt * 60) % 2 == 0 else BONE
        out[m] = BONE if int(dt * 60) % 2 == 0 else (58, 12, 34)
        img = out
    return img


# ------------------------------------------------------------------ text
_font_cache = {}
def font(name, size, wght=None):
    k = (name, int(size), wght)
    if k not in _font_cache:
        f = ImageFont.truetype(f"{FONTS}/{name}", int(size))
        if wght is not None:
            try: f.set_variation_by_axes([wght])
            except Exception: pass
        _font_cache[k] = f
    return _font_cache[k]


def text_mask(text, fnt, tracking=0.0, pad=8, vcrop=True):
    """returns uint8 alpha mask (h,w) of the text, tracking in px"""
    widths = [fnt.getlength(ch) for ch in text]
    asc, desc = fnt.getmetrics()
    w = int(sum(widths) + tracking * (len(text) - 1) + 2 * pad); h = int(asc + desc + 2 * pad)
    im = Image.new("L", (max(w, 4), max(h, 4)), 0); dr = ImageDraw.Draw(im); x = pad
    for ch, cw in zip(text, widths):
        dr.text((x, pad), ch, font=fnt, fill=255); x += cw + tracking
    a = np.array(im)
    ys, xs = np.where(a > 8)
    if len(ys):
        a = a[max(0, ys.min() - 2):ys.max() + 3, max(0, xs.min() - 2):xs.max() + 3] if vcrop else a[:, max(0, xs.min() - 2):xs.max() + 3]
    return a


def blit(img, mask, cx, cy, alpha=1.0, color=(255, 255, 255), mode="over", shadow=0.0):
    """composite an alpha mask centred at (cx,cy)"""
    mh, mw = mask.shape; x0 = int(round(cx - mw / 2)); y0 = int(round(cy - mh / 2))
    xa, ya = max(0, x0), max(0, y0); xb, yb = min(W, x0 + mw), min(H, y0 + mh)
    if xa >= xb or ya >= yb or alpha <= 0.003: return
    m = mask[ya - y0:yb - y0, xa - x0:xb - x0]
    roi = img[ya:yb, xa:xb]
    if shadow > 0:
        sm = cv2.GaussianBlur(m, (0, 0), 5 * K + 0.5)
        k = (sm.astype(np.float32) / 255.0 * shadow * alpha)[..., None]
        roi[:] = (roi.astype(np.float32) * (1 - k)).astype(np.uint8)
    if mode == "diff":
        layer = cv2.merge([((m.astype(np.uint16) * int(c * alpha)) // 255).astype(np.uint8) for c in color])
        roi[:] = cv2.absdiff(roi, layer)
    else:
        k = (m.astype(np.float32) / 255.0 * alpha)[..., None]
        roi[:] = (roi.astype(np.float32) * (1 - k) + np.array(color, np.float32) * k + 0.5).astype(np.uint8)


class Text:
    """pre-rendered text assets (built once per worker)"""
    def __init__(self):
        self.big = {}
        for L in tl.LYRICS:
            if L["text"] not in self.big:
                self.big[L["text"]] = text_mask(L["text"], font("Anton.ttf", 520 * K), tracking=6 * K)
        fi = font("PlayfairItalic.ttf", 58 * K, 500)
        self.small = {}
        for L in tl.LYRICS:
            for key in ("small", "after"):
                if key in L: self.small[L[key][0]] = text_mask(L[key][0], fi)
        fl = font("PlayfairItalic.ttf", 46 * K, 500)
        self.lines = {L["text"]: text_mask(L["text"], fl, tracking=1.5 * K) for L in tl.SMALL_LINES}
        fc = font("CormorantItalic.ttf", 62 * K, 600)
        self.cap_space = fc.getlength(" ") * 0.80
        self.cap = [[text_mask(w, fc, vcrop=False) for w, _ in c["words"]] for c in tl.CAPTIONS]
        self.cap_base = fc.getmetrics()[0]
        fo = font("Oswald.ttf", 22 * K, 500)
        self.lab = {s: text_mask(s, fo, tracking=9 * K) for s in ("ANOTHER WORLD", "SHINJUKU, TOKYO")}
        # title mask (hi-res for the zoom-through)
        self.MS = 6 if MODE == "final" else 4
        ft = font("Anton.ttf", 330 * K * self.MS)
        l1 = text_mask("DEAD MOUNT", ft, tracking=4 * K * self.MS); l2 = text_mask("DEATH PLAY", ft, tracking=4 * K * self.MS)
        tw = int(W * 0.80 * self.MS)
        l1 = cv2.resize(l1, (tw, int(l1.shape[0] * tw / l1.shape[1])), interpolation=cv2.INTER_AREA)
        l2 = cv2.resize(l2, (tw, int(l2.shape[0] * tw / l2.shape[1])), interpolation=cv2.INTER_AREA)
        gap = int(26 * K * self.MS)
        th = l1.shape[0] + gap + l2.shape[0]
        self.title = np.zeros((H * self.MS, W * self.MS), np.uint8)
        x0 = (W * self.MS - tw) // 2; y0 = (H * self.MS - th) // 2
        self.title[y0:y0 + l1.shape[0], x0:x0 + tw] = l1
        self.title[y0 + l1.shape[0] + gap:y0 + th, x0:x0 + tw] = l2
        # zoom target: thickest stroke point near the centre
        sm = cv2.resize(self.title, (W, H), interpolation=cv2.INTER_AREA)
        dist = cv2.distanceTransform((sm > 128).astype(np.uint8), cv2.DIST_L2, 5)
        yy, xx = np.mgrid[0:H, 0:W]
        score = dist - 0.02 * np.hypot(xx - W / 2, yy - H / 2)
        iy, ix = np.unravel_index(np.argmax(score), score.shape)
        self.zc = (float(ix), float(iy)); self.zdist = float(dist[iy, ix])
        # end title
        fe = font("Cinzel.ttf", 64 * K, 600)
        self.end1 = text_mask("DEAD MOUNT DEATH PLAY", fe, tracking=16 * K)
        fj = ImageFont.truetype("/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf", int(24 * K)) if os.path.exists("/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf") else None
        self.end2 = text_mask("デッドマウント・デスプレイ", fj, tracking=14 * K) if fj else None


TXT = None


def title_mask(t):
    T = tl.TITLE
    if t >= T["t_full"]: return None
    c = TXT.zc; MS = TXT.MS
    if t < T["zoom_start"]:
        u = (t - T["t0"]) / (T["zoom_start"] - T["t0"])
        s = lerp(1.0, 1.09, u) * (1 + 0.07 * math.exp(-(t - T["t0"]) / 0.07)); g = 0.0
    else:
        u = (t - T["zoom_start"]) / (T["t_full"] - T["zoom_start"])
        s_end = (W * 1.3) / max(4.0, TXT.zdist)
        s = 1.09 * (s_end / 1.09) ** (u ** 1.6); g = smooth(u * 1.4)
    # screen = (p - c) * s + c + (centre - c) * g      (p in screen-res mask coords)
    tx = c[0] - c[0] * s + (W / 2 - c[0]) * g; ty = c[1] - c[1] * s + (H / 2 - c[1]) * g
    M = np.array([[s / MS, 0, tx], [0, s / MS, ty]], np.float32)
    return cv2.warpAffine(TXT.title, M, (W, H), flags=cv2.INTER_LINEAR if s > 2 else cv2.INTER_AREA, borderMode=cv2.BORDER_CONSTANT, borderValue=0)


def draw_lyrics(img, t):
    for L in tl.LYRICS:
        if not (L["t0"] - 0.6 <= t < L["t1"]): continue
        bar = tl.letterbox(t) * H; top = bar; bot = H - bar; ch = bot - top
        if "small" in L and L["small"][1] <= t:
            a = clamp((t - L["small"][1]) / 0.08)
            m = TXT.small[L["small"][0]]
            blit(img, m, W * 0.105 + m.shape[1] / 2, top + ch * 0.060, a, BONE, shadow=0.55)
        if t < L["t0"]: continue
        dt = t - L["t0"]; d = L["t1"] - L["t0"]; u = dt / d
        if L["t1"] - t < 2.2 / 60 and int(t * 60) % 2 == 0: continue      # exit flicker
        m0 = TXT.big[L["text"]]; kind = L["kind"]; e = out_expo(dt / 0.13)
        if kind in ("tall", "tall2"):
            tw = W * 0.80; th = ch * 0.78 * lerp(0.25, 1.0, e) * (1 + 0.03 * u); cx, cy = W / 2, bot - ch * 0.10 - th / 2
        elif kind == "low":
            tw = W * 0.92; th = ch * 0.20 * lerp(2.6, 1.0, e); cx, cy = W / 2, bot - ch * 0.16
        elif kind == "wide":
            tw = W * lerp(0.55, 1.0, e) * (1 + 0.38 * u); th = ch * 0.26; cx, cy = W / 2, top + ch * 0.52
        else:  # slam
            sc = lerp(1.38, 1.0, e) * (1 + 0.035 * u)
            tw = W * 0.84 * sc; th = min(ch * 0.62, m0.shape[0] * tw / m0.shape[1])
            tw = min(tw, m0.shape[1] * th / m0.shape[0] * 1.25); cx, cy = W / 2, top + ch * 0.5
        m = cv2.resize(m0, (max(2, int(tw)), max(2, int(th))), interpolation=cv2.INTER_AREA)
        hold = L.get("hold", 0.15)
        if dt < hold:
            blit(img, m, cx, cy, 1.0, (255, 255, 255), mode="diff")
        elif dt < hold + 1.2 / 60:
            blit(img, m, cx, cy, 1.0, BONE)                                   # one-frame pop
        else:
            k = max(3, int(round(9 * K))) | 1
            edge = cv2.morphologyEx(m, cv2.MORPH_GRADIENT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
            blit(img, edge, cx, cy, 0.95, BONE, shadow=0.35)
        if "after" in L and L["after"][1] <= t:
            a = clamp((t - L["after"][1]) / 0.08)
            m = TXT.small[L["after"][0]]
            blit(img, m, W * 0.895 - m.shape[1] / 2, top + ch * 0.060, a, BONE, shadow=0.55)


def draw_small_lines(img, t):
    for L in tl.SMALL_LINES:
        if not (L["t0"] <= t < L["t1"]): continue
        a = min(clamp((t - L["t0"]) / 0.18), clamp((L["t1"] - t) / 0.20))
        m = TXT.lines[L["text"]]; bar = tl.letterbox(t) * H
        rise = (1 - out_cubic((t - L["t0"]) / 0.35)) * 10 * K
        if L.get("center"):
            blit(img, m, W / 2, H / 2 + rise, a, BONE, shadow=0.85)
        else:
            blit(img, m, W * 0.075 + m.shape[1] / 2, H - bar - 58 * K + rise, a, BONE, shadow=0.7)
    if 19.72 <= t < 21.34:
        a = min(clamp((t - 19.72) / 0.2), clamp((21.34 - t) / 0.12)) * 0.85; bar = tl.letterbox(t) * H
        m = TXT.lab["ANOTHER WORLD"]; blit(img, m, W * 0.045 + m.shape[1] / 2, bar + 40 * K, a, BONE, shadow=0.6)
        m = TXT.lab["SHINJUKU, TOKYO"]; blit(img, m, W * 0.955 - m.shape[1] / 2, bar + 40 * K, a, BONE, shadow=0.6)


def draw_captions(img, t):
    for c, masks in zip(tl.CAPTIONS, TXT.cap):
        if not (c["t"] - 0.05 <= t < c["end"] + 0.4): continue
        if c.get("hard_end") and t >= c["hard_end"]: continue
        fade = clamp((c["end"] + 0.4 - t) / 0.4)
        bar = tl.letterbox(t) * H
        cy = H - bar / 2 if bar > 0.09 * H else H * 0.885
        total = sum(m.shape[1] for m in masks) + TXT.cap_space * (len(masks) - 1)
        x = W / 2 - total / 2
        hmax = max(m.shape[0] for m in masks)
        for (wd, off), m in zip(c["words"], masks):
            a = clamp((t - (c["t"] + off)) / 0.16) * fade
            rise = (1 - out_cubic((t - (c["t"] + off)) / 0.3)) * 7 * K
            # bottom-align words on a common baseline (descenders ignored -> align by bottom of x-height approx)
            blit(img, m, x + m.shape[1] / 2, cy + (hmax - m.shape[0]) / 2 * 0.0 + rise, a, BONE, shadow=0.75)
            x += m.shape[1] + TXT.cap_space


# ------------------------------------------------------------------ post
_noise = None; _vig = None
def post(img, t, acc, n):
    global _noise, _vig
    # glow
    ga = 0.10 + acc["glow"]
    sm = cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    br = cv2.subtract(sm, np.full_like(sm, 140))
    br = cv2.GaussianBlur(br, (0, 0), W / 4 * 0.022)
    img = cv2.addWeighted(img, 1.0, cv2.resize(br, (W, H), interpolation=cv2.INTER_LINEAR), ga * 2.2, 0)
    # radial chromatic aberration
    e = (0.7 + acc["rgb"]) * 0.0011
    if e > 0.0004:
        b, g, r = cv2.split(img)
        Mr = np.array([[1 + e, 0, -e * W / 2], [0, 1 + e, -e * H / 2]], np.float32)
        Mb = np.array([[1 - e, 0, e * W / 2], [0, 1 - e, e * H / 2]], np.float32)
        r = cv2.warpAffine(r, Mr, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
        b = cv2.warpAffine(b, Mb, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
        img = cv2.merge([b, g, r])
    # flashes / white-out
    fl = acc["flash"]
    if 15.40 <= t < 16.45: fl += smooth((t - 15.40) / 0.37) if t < 15.77 else 1 - smooth((t - 15.77) / 0.68)
    if 16.67 <= t < 17.0: fl += 0.35 * (1 - (t - 16.67) / 0.33)
    if tl.CHORUS <= t < tl.CHORUS + 0.3: fl += 0.55 * (1 - (t - tl.CHORUS) / 0.3)
    if fl > 0.004:
        img = cv2.addWeighted(img, 1.0, np.full_like(img, 255), min(fl, 1.0), 0)
    # grain
    if _noise is None:
        rng = np.random.default_rng(7)
        _noise = []
        for _ in range(6):
            nz = rng.normal(128, 26, (H // 2 + 1, W // 2 + 1)).astype(np.float32)
            nz = cv2.resize(nz, (W, H), interpolation=cv2.INTER_CUBIC) if K > 0.6 else nz[:H, :W] if nz.shape[0] >= H else cv2.resize(nz, (W, H))
            nz = np.clip(nz, 0, 255).astype(np.uint8)
            _noise.append(cv2.merge([nz, nz, nz]))
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r2 = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
        v = np.clip(1.0 - 0.30 * np.clip(r2 - 0.25, 0, None) ** 1.3, 0.35, 1.0)
        _vig = cv2.merge([(v * 255).astype(np.uint8)] * 3)
    amt = 0.17 if t < 5.86 else 0.085
    img = cv2.addWeighted(img, 1.0, _noise[(n // max(1, FPS // 24)) % 6], amt, -128 * amt)
    img = cv2.multiply(img, _vig, scale=1 / 255.0)
    return img


def frame_at(n):
    t = n / FPS
    acc = accents(t)
    canvas = np.zeros((H, W, 3), np.uint8)
    act = [s for s in tl.SHOTS if s["t0"] <= t < s["t1"]]
    for i, s in enumerate(act):
        img = render_shot(s, t, acc)
        a = clamp((t - s["t0"]) / s["fin"]) if s["fin"] > 0 else 1.0
        if i == len(act) - 1 and s["fout"] > 0: a *= clamp((s["t1"] - t) / s["fout"])
        if s["region"]:
            gap = int(5 * K); pw = W // 2 - gap
            e = out_expo((t - s["t0"]) / 0.32)
            off = int((1 - e) * H) * (-1 if s["region"] == "L" else 1)
            panel = img[:, W // 4:W // 4 + pw]
            x0 = 0 if s["region"] == "L" else W - pw
            ya, yb = max(0, off), min(H, H + off)
            if yb > ya: canvas[ya:yb, x0:x0 + pw] = panel[ya - off:yb - off]
        elif a >= 0.999: canvas = img
        elif a > 0.001: canvas = cv2.addWeighted(canvas, 1 - a, img, a, 0)
    # title: footage only inside the letters
    T = tl.TITLE
    if T["t0"] <= t < T["t_full"]:
        m = title_mask(t)
        if m is not None:
            zp = clamp((t - T["zoom_start"]) / (T["t_full"] - T["zoom_start"]))
            lift = 0.42 * (1 - zp) + 0.6 * math.exp(-(t - T["t0"]) / 0.09)
            fill = np.empty_like(canvas); fill[:] = (150, 70, 120)
            canvas = cv2.addWeighted(canvas, 1.0, fill, lift, 0)
            canvas = cv2.multiply(canvas, cv2.merge([m, m, m]), scale=1 / 255.0)
            if zp < 0.5:
                k = max(3, int(round(5 * K))) | 1
                edge = cv2.morphologyEx(m, cv2.MORPH_GRADIENT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
                blit(canvas, edge, W / 2, H / 2, 0.55 * (1 - 2 * zp), BONE)
    draw_lyrics(canvas, t)
    canvas = post(canvas, t, acc, n)
    draw_small_lines(canvas, t)
    # letterbox
    bar = int(round(tl.letterbox(t) * H))
    if bar > 0: canvas[:bar] = 0; canvas[H - bar:] = 0
    draw_captions(canvas, t)
    # end title
    E = tl.END_TITLE
    if t >= E["t0"]:
        a = min(smooth((t - E["t0"] - 0.25) / 0.45), smooth((E["t1"] - 0.08 - t) / 0.45))
        blit(canvas, TXT.end1, W / 2, H / 2 - 8 * K, a, BONE)
        if TXT.end2 is not None: blit(canvas, TXT.end2, W / 2, H / 2 + 54 * K, a * 0.7, BONE)
    return canvas


def worker(args):
    global TXT
    wi, n0, n1 = args
    cv2.setNumThreads(1)
    TXT = Text()
    out = f"{ROOT}/out/{MODE}_part{wi}.mp4"
    enc = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709",
           "-color_trc", "bt709", "-color_range", "tv", "-c:v", "libx264", "-preset", "medium" if MODE == "final" else "veryfast",
           "-crf", "15" if MODE == "final" else "20", "-threads", "2", out]
    p = subprocess.Popen(enc, stdin=subprocess.PIPE)
    for n in range(n0, n1):
        p.stdin.write(frame_at(n).tobytes())
    p.stdin.close(); p.wait()
    return out


if __name__ == "__main__":
    os.makedirs(f"{ROOT}/out", exist_ok=True)
    n0, n1 = int(round(T0 * FPS)), int(round(T1 * FPS))
    step = math.ceil((n1 - n0) / NW)
    jobs = [(i, n0 + i * step, min(n1, n0 + (i + 1) * step)) for i in range(NW) if n0 + i * step < n1]
    with mp.Pool(len(jobs)) as pool: parts = pool.map(worker, jobs)
    with open(f"{ROOT}/out/{MODE}_parts.txt", "w") as f:
        for p in parts: f.write(f"file '{p}'\n")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{ROOT}/out/{MODE}_parts.txt", "-c", "copy",
                    f"{ROOT}/out/{MODE}_video.mp4"], check=True)
    print("wrote", f"{ROOT}/out/{MODE}_video.mp4", n1 - n0, "frames")
