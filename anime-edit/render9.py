"""V9 renderer. One language from start to finish: black-and-white manga pages, a camera that travels between panels with real
motion blur, colour only where something supernatural glows. usage: render9.py [draft|final] [t0 t1]"""
import os, sys, json, math
os.environ["TLMOD"] = "tl9"
import subprocess, multiprocessing as mp
from r2core import *                      # tl = tl9
import render8 as R8
import render7 as R7
import render2 as R2
import render4 as R4
import render6 as R6
import fxcomp as X
import fxtype as FT

SH = tl.BY; A9 = {}; PG = {}
PAPER = (236, 238, 240); INKC = (14, 12, 14); WHITE = (246, 246, 244); CRIM = (40, 30, 215); PAGEC = (10, 9, 11)
CAPF = f"{ROOT}/fonts3/ComicNeue-BoldItalic.ttf"; IMPF = f"{ROOT}/fonts/Anton.ttf"; SUBF = f"{ROOT}/fonts3/BarlowSemiCond-XBold.ttf"
P = R8.P; PTS = R8.PTS; DW = R7.DW
R8.LOOKS.update(ink=lambda im: X.ink2(im), inkg=lambda im: X.ink2(im, glow=1.0), inkd=lambda im: X.ink2(im, solid=0.30, tone_hi=0.74, glow=1.0))


_NFR = {}
def fidx9(s, t):
    k = s["name"]
    if k not in _NFR: _NFR[k] = len(CLIPS.get(s))
    d = s["t1"] - s["t0"]; dt = clamp(t - s["t0"], 0.0, d); st_ = src_time(s, d - dt) if s.get("rev") else src_time(s, dt)
    return max(0, min(_NFR[k] - 1, int(st_ * tl.SRC_FPS + 1e-4)))
R8.fidx = fidx9
def base9(name, t, look="raw"):
    s = SH[name]; fi = fidx9(s, t)
    return R8._lru(R8._LC, (name, fi, look), lambda: R8.LOOKS[look](apply_grade(CLIPS.get(s)[fi], s["grade"])), 90)
R8.base = base9


# ======================================================================== matrices
def T3(dx, dy): return np.array([[1, 0, dx], [0, 1, dy], [0, 0, 1]], np.float64)
def S3(sx, sy=None): return np.diag([sx, sx if sy is None else sy, 1.0])
def R3(deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], np.float64)
def cam3(c): return T3(W / 2, H / 2) @ R3(c[3]) @ S3(c[2] * K) @ T3(-c[0], -c[1])
def xf(M, pts): p = np.asarray(pts, np.float64); return p @ M[:2, :2].T + M[:2, 2]
def bbox(pts): p = np.asarray(pts, np.float64); return p[:, 0].min(), p[:, 1].min(), p[:, 0].max(), p[:, 1].max()
def fr(pts, margin=1.06, rot=0.0, ox=0.0, oy=0.0):
    """camera pose that frames a polygon."""
    x0, y0, x1, y1 = bbox(pts); return ((x0 + x1) / 2 + ox, (y0 + y1) / 2 + oy, min(1920.0 / ((x1 - x0) * margin), 1080.0 / ((y1 - y0) * margin)), rot)
EASE = dict(io=lambda u: X.ease_io(u, 3), expo=out_expo, smooth=smooth, inn=lambda u: clamp(u) ** 2.4, out=out_cubic, lin=clamp)


# ======================================================================== type
def cap_make(rows, pad=(30, 24), gap=0.55, shadow=8):
    """manga caption box. rows = [(size, [(word, t_on), ...]), ...] -> dict(pm, a, rects=[(x0, y0, x1, y1, t_on)], w, h) at K scale."""
    lay = []; wmax = 0.0; y = pad[1] * K
    for size, words in rows:
        f = FT.font(CAPF, size * K); sp = f.getlength(" ") * 0.9; x = pad[0] * K; bb = f.getbbox("H"); ct, ch = bb[1], bb[3] - bb[1]; ws = []
        for w_, tt in words:
            wl = f.getlength(w_); ws.append((w_, tt, x, wl)); x += wl + sp
        lay.append((f, ct, ch, y, ws)); wmax = max(wmax, x - sp); y += ch * (1 + gap)
    bw = int(wmax + pad[0] * K); bh = int(y - lay[-1][2] * gap + pad[1] * K); sh = int(shadow * K)
    im = Image.new("L", (bw, bh), 0); d = ImageDraw.Draw(im); rects = []; st = 1 if K > 0.75 else 0
    for f, ct, ch, yy, ws in lay:
        for w_, tt, x, wl in ws:
            d.text((x, yy - ct), w_, font=f, fill=255, stroke_width=st, stroke_fill=255)
            rects.append((int(x - 4), int(yy - ch * 0.22), int(x + wl + 6), int(yy + ch * 1.30), tt))
    tm = np.array(im).astype(np.float32) / 255.0; bd = max(2, int(round(5 * K)))
    col = np.zeros((bh + sh, bw + sh, 3), np.float32); al = np.zeros((bh + sh, bw + sh), np.float32)
    col[sh:, sh:] = INKC; al[sh:, sh:] = 1.0                                          # hard drop shadow
    box = np.empty((bh, bw, 3), np.float32); box[:] = PAPER; box = box * (1 - tm[..., None]) + np.asarray(INKC, np.float32) * tm[..., None]
    box[:bd] = INKC; box[-bd:] = INKC; box[:, :bd] = INKC; box[:, -bd:] = INKC
    col[:bh, :bw] = box; al[:bh, :bw] = 1.0
    return dict(pm=(col * al[..., None]).astype(np.uint8), a=(al * 255).astype(np.uint8), rects=rects, w=bw + sh, h=bh + sh, bd=bd, bw=bw, bh=bh)


def cap_layer(cap, t):
    pm = cap["pm"]; hid = [r for r in cap["rects"] if r[4] is not None and t < r[4] + 0.07]
    if not hid: return pm, cap["a"]
    pm = pm.copy(); bd = cap["bd"]
    for x0, y0, x1, y1, tt in hid:
        k = 1.0 - clamp((t - tt) / 0.07) if t >= tt else 1.0
        roi = pm[max(bd, y0):min(y1, cap["bh"] - bd), max(bd, x0):min(x1, cap["bw"] - bd)]; roi[:] = (roi.astype(np.float32) * (1 - k) + np.asarray(PAPER, np.float32) * k).astype(np.uint8)
    return pm, cap["a"]


def cap_draw(canvas, cap, t, t_on, t_off, cx, cy, s=1.0, rot=0.0):
    """centre (cx,cy) in screen px. pops in, cuts out."""
    if not (t_on <= t < t_off): return
    e = out_back(clamp((t - t_on) / 0.14), 1.8); f = clamp((t_off - t) / 0.06)
    pm, a = cap_layer(cap, t); X.place(canvas, pm, a, cx, cy, s * (0.6 + 0.4 * e), rot, clamp((t - t_on) / 0.05) * f)


def imp(word, size, fill=WHITE, ext=INKC, tracking=4, shear=0.12, depth=0.040):
    m = FT.shear(FT.glyphs(word, IMPF, size * K, tracking=tracking * K), shear); return FT.vrens(m, fill=fill, depth=depth, angle=45, ext=ext, shadow=0)


def sub(text, size, col=WHITE, tracking=6): return FT.flat(FT.glyphs(text, SUBF, size * K, tracking=tracking * K), col)


def setup9():
    R8.setup8(); k = K
    A9["face"] = imp("FACE", 520)
    A9["f2f"] = [imp("FACE", 210), imp("TO", 210, fill=CRIM), imp("FACE", 210)]
    A9["what"] = imp("WHAT?", 330, depth=0.05)
    A9["go"] = R8.A8["go"]
    R7.X7["sig"] = FT.flat(FT.shear(FT.glyphs("SHIGAMI", IMPF, 40 * k, tracking=3 * k), 0.12), (236, 236, 236))
    R7.X7["b1"] = FT.flat(FT.glyphs("AN EDIT BY   SHIGAMI", SUBF, 40 * k, tracking=12 * k), (32, 28, 30))
    R7.X7["b2"] = FT.flat(FT.glyphs("MUSIC  “SYNTHETIC”     FOOTAGE  DEAD MOUNT DEATH PLAY   EP. 01 · 02 · 04 · 05", SUBF, 20 * k, tracking=4 * k), (70, 66, 68))
    w = DW["intro"]; L = tl.LYR
    A9["c_q"] = cap_make([(66, [(x_, w[i][0] + 0.30) for i, x_ in enumerate(("CAN", "YOU", "SAY", "YOUR", "OWN", "NAME?"))])])
    A9["c_a1"] = cap_make([(66, [(x_, w[6 + i][0]) for i, x_ in enumerate(("THE", "BODY", "THAT"))]),
                           (66, [(x_, w[9 + i][0]) for i, x_ in enumerate(("I’M", "IN", "RIGHT", "NOW,"))])])
    A9["c_a2"] = cap_make([(60, [(x_, w[13 + i][0]) for i, x_ in enumerate(("ITS", "NAME", "IS"))]), (96, [("POLKA", w[16][0])]), (96, [("SHINOYAMA.", w[17][0])])], gap=0.45)
    A9["c_tears"] = cap_make([(60, [("…WITH", None), ("TEARS.", None)])])
    A9["c_demons"] = cap_make([(60, [("IT’S", None), ("THESE", None), ("DEMONS.", None)])])
    A9["c_ask"] = cap_make([(72, [("I’M", None), ("ASKING—", None)])])
    A9["c_mirror"] = cap_make([(60, [(x_, tt) for tt, x_ in L["mirror"]])])
    A9["c_recog"] = cap_make([(60, [(x_, tt) for tt, x_ in L["recog"][:3]]), (84, [(x_, tt) for tt, x_ in L["recog"][3:]])], gap=0.45)
    A9["c_gone"] = cap_make([(60, [(x_, tt) for tt, x_ in L["gone"][:4]]), (84, [(x_, tt) for tt, x_ in L["gone"][4:]])], gap=0.45)
    A9["c_mask"] = cap_make([(72, [(x_, tt) for tt, x_ in L["mask"]])])
    A9["c_name"] = cap_make([(96, [("POLKA", None), ("SHINOYAMA", None)])], pad=(34, 26))
    tg = DW["tag"]; ts = [x[0] for x in tg]; ts[0] = 40.84
    A9["c_t1"] = cap_make([(64, [("WHOEVER", ts[0]), ("YOU", ts[1]), ("ARE,", ts[2])])])
    A9["c_t2"] = cap_make([(64, [("IT", ts[3]), ("SEEMS", ts[4]), ("YOU’RE", ts[5]), ("NOT", ts[6])]), (64, [("POLKA", ts[7]), ("SHINOYAMA,", ts[8])])])
    A9["c_t3"] = cap_make([(64, [("AT", ts[9]), ("LEAST", ts[10]), ("NOT", ts[11])]), (84, [("ON", ts[12]), ("THE", ts[13]), ("INSIDE.", ts[14])])], gap=0.45)
    A9["title"] = imp("THE CORPSE GOD", 150, fill=WHITE, depth=0.05)
    build_pages()


# ======================================================================== panels, pages, camera
def content(shot, ts, look, tot):
    """look-treated frame of a shot at shot-time ts; half / quarter resolution copies when it will be drawn small (no moire)."""
    img = R8.base(shot, ts, look)
    if tot >= 0.62: return img, 1.0
    f = 0.5 if tot >= 0.31 else 0.25; fi = R8.fidx(SH[shot], ts)
    return R8._lru(R8._LC, ("mip", shot, fi, look, f), lambda: cv2.resize(img, None, fx=f, fy=f, interpolation=cv2.INTER_AREA), 60), f


class Pn:
    def __init__(s, key, pts, shot, t0, look="ink", fit=(1.0, 1.05, 0.5, 0.5), life=1.0, ent=(0, 0, 0, 1.0), edur=0.18, border=9, fx=(), brk=None,
                 swap=None, rate=1.0, front=False, flip=False, mask_fn=None, t1=None, wipe=None):
        s.key, s.pts, s.shot, s.t0, s.look, s.fit, s.life, s.ent, s.edur = key, np.asarray(pts, np.float64), shot, t0, look, fit, life, ent, edur
        s.border, s.fx, s.brk, s.swap, s.rate, s.front, s.flip, s.mask_fn, s.t1, s.wipe = border, fx, brk, swap, rate, front, flip, mask_fn, t1, wipe

    def E(s, t):
        u = (t - s.t0) / s.edur
        if u >= 1 or s.ent == (0, 0, 0, 1.0): return np.eye(3)
        e = out_cubic(u); c = s.pts.mean(0); dx, dy, rot, s0 = s.ent; dx *= 0.6; dy *= 0.6
        return T3(c[0] + dx * (1 - e), c[1] + dy * (1 - e)) @ R3(rot * (1 - e)) @ S3(lerp(s0, 1.0, e)) @ T3(-c[0], -c[1])

    def F(s, t, fit=None, flip=None):
        x0, y0, x1, y1 = bbox(s.pts); fit = fit or s.fit; z0, z1, fx, fy = fit[:4]; fx1, fy1 = (fit[4], fit[5]) if len(fit) > 4 else (fx, fy)
        lu = smooth(clamp((t - s.t0) / s.life)); sc = max((x1 - x0) / 1920.0, (y1 - y0) / 1080.0) * lerp(z0, z1, lu)
        hx = (x1 - x0) / (2 * sc * 1920.0); hy = (y1 - y0) / (2 * sc * 1080.0); flp = s.flip if flip is None else flip
        fxx = min(max(lerp(fx, fx1, lu), hx), 1 - hx); fyy = min(max(lerp(fy, fy1, lu), hy), 1 - hy)
        if flp: fxx = 1 - fxx
        Fm = np.array([[sc / K, 0, (x0 + x1) / 2 - sc * fxx * 1920], [0, sc / K, (y0 + y1) / 2 - sc * fyy * 1080], [0, 0, 1]])
        if flp: Fm = Fm @ np.array([[-1, 0, W], [0, 1, 0], [0, 0, 1.0]])
        return Fm, sc

    def ts(s, t, shot=None):
        S_ = SH[shot or s.shot]; return S_["t0"] + clamp((t - s.t0) * s.rate, 0.0, S_["t1"] - S_["t0"] - 1e-3)

    def warp(s, shot, look, t, CE, z, roi, fit=None, flip=None, matte=False):
        x0, y0, x1, y1 = roi; Fm, sc = s.F(t, fit, flip); ts = s.ts(t, shot)
        if matte:
            m = R8.basem(shot, ts)
            if m is None: return None
            M = T3(-x0, -y0) @ CE @ Fm; return cv2.warpAffine(m, M[:2], (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        img, f = content(shot, ts, look, sc * z); M = T3(-x0, -y0) @ CE @ Fm @ S3(1 / f)
        return cv2.warpAffine(img, M[:2], (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)

    def draw(s, canvas, C, t, z):
        if t < s.t0 or (s.t1 is not None and t >= s.t1): return
        CE = C @ s.E(t); mp_ = s.pts if s.mask_fn is None else np.asarray(s.mask_fn(t), np.float64); ps = xf(CE, mp_)
        x0 = int(max(0, math.floor(ps[:, 0].min()) - 2)); y0 = int(max(0, math.floor(ps[:, 1].min()) - 2))
        x1 = int(min(W, math.ceil(ps[:, 0].max()) + 2)); y1 = int(min(H, math.ceil(ps[:, 1].max()) + 2))
        if x1 - x0 < 4 or y1 - y0 < 4: return
        roi = (x0, y0, x1, y1); w_, h_ = x1 - x0, y1 - y0; cont = s.warp(s.shot, s.look, t, CE, z, roi)
        pc = ps.mean(0) - (x0, y0)
        if s.swap is not None and t >= s.swap["t"]:              # change to another look / shot inside the panel (circle flood or fade)
            sw = s.swap; u = clamp((t - sw["t"]) / sw["dur"]); b = s.warp(sw.get("shot", s.shot), sw.get("look", "raw"), t, CE, z, roi, sw.get("fit"), sw.get("flip"))
            if sw.get("mode", "circle") == "circle":
                m = np.zeros((h_, w_), np.uint8); r = out_cubic(u) * 0.62 * math.hypot(w_, h_) * 1.1
                cv2.circle(m, (int(pc[0]), int(pc[1])), int(r), 255, -1, cv2.LINE_AA); m = cv2.GaussianBlur(m, (0, 0), 6 * K + 0.5)
                a3 = cv2.merge([m] * 3); cont = cv2.add(cv2.multiply(cont, 255 - a3, scale=1 / 255.0), cv2.multiply(b, a3, scale=1 / 255.0))
            else: cont = cv2.addWeighted(cont, 1 - smooth(u), b, smooth(u), 0)
        if s.wipe is not None and t >= s.wipe[0]:                # the drawing is rubbed out, left to right, down to bare paper
            u = clamp((t - s.wipe[0]) / s.wipe[1]); xx = np.linspace(0, 1, w_, dtype=np.float32)[None, :]
            nz = A9.setdefault("wipe_nz", cv2.resize(np.random.default_rng(5).uniform(-1, 1, (24, 40)).astype(np.float32), (1920, 1080), interpolation=cv2.INTER_CUBIC))
            g = np.clip((u * 1.5 - xx - 0.12 * nz[:h_, :w_] - 0.1) / 0.10, 0, 1)[..., None]
            cont = (cont.astype(np.float32) * (1 - g * 0.93) + np.asarray(PAPER, np.float32) * g * 0.93).astype(np.uint8)
        for f in s.fx:
            if f[0] == "focus":
                fl = X.focus_lines(h_, w_, pc[0] + f[5] * w_ if len(f) > 5 else pc[0], pc[1] + (f[6] * h_ if len(f) > 6 else 0), X.on2(t) + sum(map(ord, s.key)), n=f[1], r_in=f[2], r_jit=0.2)
                X.paint(cont, f[4], fl * f[3])
            elif f[0] == "speed":
                sl = X.speed_lines(h_, w_, X.on2(t, 24) + sum(map(ord, s.key)), angle=f[1], n=f[2]); X.paint(cont, f[4], sl * f[3])
        m = np.zeros((h_, w_), np.uint8); q = np.int32(np.round((ps - (x0, y0)) * 8)); cv2.fillPoly(m, [q], 255, cv2.LINE_AA, 3)
        a3 = cv2.merge([m] * 3); r_ = canvas[y0:y1, x0:x1]
        cv2.multiply(r_, 255 - a3, dst=r_, scale=1 / 255.0); cv2.add(r_, cv2.multiply(cont, a3, scale=1 / 255.0), dst=r_)
        if s.border: cv2.polylines(r_, [q], True, WHITE, max(2, int(round(s.border * z * K))), cv2.LINE_AA, 3)

    def draw_brk(s, canvas, C, t, z):
        b = s.brk
        if b is None or t < s.t0 + b.get("t", 0.0) or (s.t1 is not None and t >= s.t1): return
        u = clamp((t - s.t0 - b.get("t", 0.0)) / 0.22); e = out_back(u, 1.6); x0, y0, x1, y1 = bbox(s.pts)
        ax, ay = (x0 + x1) / 2, y1; sc = lerp(1.0, b.get("s", 1.07), e)
        CE = C @ s.E(t) @ T3(ax, ay) @ S3(sc) @ T3(-ax, -ay) @ T3(0, -b.get("lift", 10) * e); roi = (0, 0, W, H)
        m = s.warp(b.get("shot", s.shot), None, t, CE, z, roi, matte=True)
        if m is None or m.max() < 40: return
        img = s.warp(b.get("shot", s.shot), b.get("look", "raw"), t, CE, z, roi)
        R8.stick_full(canvas, img, m, px=b.get("px", 6) * z, col=WHITE, px2=3 * z, col2=INKC, shadow=(10 * z, 8 * z, 10 * z, 0.55))


class Page:
    def __init__(s, key, panels, pose0, cams, caps=(), sfx=(), hits=(), extra=None, creep=0.035):
        s.key, s.panels, s.pose0, s.cams, s.caps, s.sfx, s.hits, s.extra, s.creep = key, panels, pose0, cams, caps, sfx, hits, extra, creep
        s.by = {p.key: p for p in panels}

    def cam(s, t):
        pose = s.pose0; t_arr = None; c = None
        def crept(tt): return pose if t_arr is None else (pose[0], pose[1], pose[2] * (1 + s.creep * clamp((tt - t_arr) / 1.2)), pose[3])
        for t0, t1, tgt, ez in s.cams:
            if t >= t1: pose, t_arr = tgt, t1; continue
            if t > t0:
                a = crept(t0); u = EASE[ez]((t - t0) / (t1 - t0)); c = (lerp(a[0], tgt[0], u), lerp(a[1], tgt[1], u), a[2] * (tgt[2] / a[2]) ** u, lerp(a[3], tgt[3], u))
            break
        if c is None: c = crept(t)
        zp = 0.0; sx = sy = 0.0
        for h0, st in s.hits:
            d = t - h0
            if 0 <= d < 0.5:
                zp += 0.035 * st * math.exp(-d / 0.08); a_ = 7.0 * st * math.exp(-d / 0.10); jx, jy = X.shake(t, a_, h0); sx += jx; sy += jy
        return (c[0] + sx / c[2], c[1] + sy / c[2], c[2] * (1 + zp), c[3] + 0.25 * math.sin(t * 0.8 + len(s.key)))

    def moving(s, t):
        a, b = s.cam(t), s.cam(t + 1.0 / FPS)
        if math.hypot(b[0] - a[0], b[1] - a[1]) * a[2] * K > 2.0 or abs(b[2] / a[2] - 1) > 0.0015: return True
        for p in s.panels:
            if p.ent != (0, 0, 0, 1.0) and -0.02 <= t - p.t0 < p.edur + 0.03: return True
            if p.brk is not None and -0.02 <= t - p.t0 - p.brk.get("t", 0) < 0.25: return True
            if p.mask_fn is not None and -0.02 <= t - p.t0 < 0.4: return True
        for c in s.caps:
            if -0.02 <= t - c["t0"] < 0.16: return True
        for f in s.sfx:
            if -0.02 <= t - f["t0"] < 0.14: return True
        return False

    def render(s, t):
        canvas = np.empty((H, W, 3), np.uint8); canvas[:] = PAGEC; c = s.cam(t); C = cam3(c); z = c[2]
        back = [p for p in s.panels if not p.front]; front = [p for p in s.panels if p.front]
        for p in back: p.draw(canvas, C, t, z)
        for p in back: p.draw_brk(canvas, C, t, z)
        for p in front: p.draw(canvas, C, t, z)
        for p in front: p.draw_brk(canvas, C, t, z)
        if s.extra: s.extra(canvas, C, t, z)
        for f in s.sfx:
            if f["t0"] <= t < f["t1"]:
                d = t - f["t0"]; e = out_back(clamp(d / 0.10), 2.4); q = xf(C, [(f["x"], f["y"])])[0]; jx, jy = X.shake(t, 3 * K, f["t0"])
                X.place(canvas, *f["L"], q[0] + jx, q[1] + jy, f.get("s", 1.0) * z * (0.4 + 0.6 * e), c[3] + f.get("rot", 0), clamp((f["t1"] - t) / 0.07))
        for cp in s.caps:
            if cp["t0"] <= t < cp["t1"]:
                cap = A9[cp["cap"]]; cs = cp.get("s", 1.0); q = xf(C, [(cp["x"] + cs * cap["w"] / (2 * K), cp["y"] + cs * cap["h"] / (2 * K))])[0]
                cap_draw(canvas, cap, t, cp["t0"], cp["t1"], q[0], q[1], z * cp.get("s", 1.0), c[3] + cp.get("rot", 0))
        return canvas


def whipk(t, tgt, pre=0.10, post=0.08, ez="io"): return (t - pre, t + post, tgt, ez)


def build_pages():
    FO = lambda n=100, rin=0.32, st=0.7, col=INKC: ("focus", n, rin, st, col)
    # ---------------------------------------------------------------- verse page 10.43 - 16.13
    A = [(40, 40), (2360, 40), (2360, 860), (40, 1000)]; B = [(40, 1060), (1040, 1000), (1040, 1760), (40, 1760)]
    C_ = [(1100, 996), (2360, 920), (2360, 1760), (1100, 1760)]; D = [(40, 1820), (2360, 1820), (2360, 2300), (40, 2380)]
    E_ = [(40, 2440), (880, 2400), (880, 2960), (40, 2960)]; F_ = [(940, 2396), (2360, 2360), (2360, 2960), (940, 2960)]
    G = [(-60, 1330), (2460, 1230), (2460, 1710), (-60, 1810)]
    def gmask(t):
        e = out_expo((t - 15.21) / 0.28); g = np.asarray(G, np.float64); cy = 1520.0 + (g[:, 0] - 1200) * -0.0397
        g2 = g.copy(); g2[:, 1] = cy + (g[:, 1] - cy) * (0.06 + 0.94 * e); return g2
    pv = [Pn("A", A, "V4", 10.43, fit=(1.0, 1.07, 0.5, 0.28), life=0.95, fx=(("speed", -28, 32, 0.30, INKC),)),
          Pn("B", B, "V5a", 11.38, fit=(1.05, 1.10, 0.5, 0.42), life=0.6, ent=(-900, 0, -4, 1.0)),
          Pn("C", C_, "V5b", 11.68, look="inkg", fit=(1.0, 1.06, 0.5, 0.5), life=0.67, ent=(900, 0, 4, 1.0), fx=(FO(110, 0.36, 0.6),), brk=dict(look="inkg", s=1.08, t=0.04)),
          Pn("D", D, "V6", 12.35, look="inkg", fit=(1.0, 1.08, 0.35, 0.55, 0.65, 0.55), life=0.93, ent=(0, 700, 0, 1.0)),
          Pn("E", E_, "V7", 13.28, look="inkg", fit=(1.25, 1.35, 0.5, 0.60), life=0.98, ent=(-900, 0, 0, 1.0)),
          Pn("F", F_, "V8", 14.26, look="inkg", fit=(1.0, 1.08, 0.5, 0.45), life=0.95, ent=(900, 0, 0, 1.0), rate=0.8),
          Pn("G", G, "V9", 15.21, look="raw", fit=(1.0, 1.0, 0.555, 0.47), life=0.9, mask_fn=gmask, border=7, front=True, rate=1.0)]
    whole = (1200, 1500, 0.345, -3.0)
    PG["V"] = Page("V", pv, fr(A, 0.90, 1.5), [(10.43, 10.72, fr(A, 1.05), "expo"), whipk(11.38, fr(B, 1.12, -1.5)), whipk(11.68, fr(C_, 1.10, 1.5)),
                                              whipk(12.35, fr(D, 1.05)), whipk(13.28, fr(E_, 1.30, 0, 60, 0), 0.12, 0.10), whipk(14.26, fr(F_, 1.08, 0, 0, -20)),
                                              (15.11, 15.34, whole, "io"), (15.42, 15.92, (1200, 1520, 0.82, 0.0), "inn")],
                   caps=[dict(cap="c_tears", x=70, y=2870, t0=tl.LYR["tears"], t1=14.20), dict(cap="c_demons", x=980, y=2420, t0=tl.LYR["demons"], t1=15.30)],
                   sfx=[dict(L=A9["go"], x=2180, y=2520, t0=14.26, t1=15.15, rot=-8, s=0.8), dict(L=A9["go"], x=2260, y=2740, t0=14.50, t1=15.15, rot=6, s=0.8)],
                   hits=[(10.43, 0.9), (11.38, 0.5), (11.68, 1.0), (12.35, 0.9), (13.28, 0.4), (14.26, 0.9), (15.21, 0.8)])
    # ---------------------------------------------------------------- drop page 1: the past life 16.13 - 19.96
    P0 = [(36, 40), (1100, 64), (1046, 1044), (26, 1032)]; P1 = [(1150, 40), (1886, 26), (1894, 506), (1124, 526)]
    P2 = [(1112, 572), (1890, 548), (1882, 1046), (1080, 1052)]; P3 = [(-80, 640), (2000, 300), (2000, 520), (-80, 900)]; P4 = [(36, 1150), (1886, 1150), (1886, 2190), (36, 2190)]
    pd = [Pn("P0", P0, "D2b", 15.80, look="inkg", fit=(1.05, 1.12, 0.60, 0.48), life=1.2, fx=(FO(100, 0.34, 0.75),), rate=0.6),
          Pn("P1", P1, "D1", 16.85, look="inkg", fit=(1.0, 1.10, 0.5, 0.5), life=0.72, ent=(900, -300, 5, 1.0)),
          Pn("P2", P2, "D3", 17.57, look="inkg", fit=(1.0, 1.10, 0.62, 0.42), life=0.72, ent=(700, 500, -5, 1.0)),
          Pn("P3", P3, "D4", 18.30, look="inkg", fit=(1.0, 1.10, 0.5, 0.5), life=0.7, ent=(-2300, 380, 0, 1.0), edur=0.16, front=True, fx=(("speed", -9, 50, 0.5, WHITE),)),
          Pn("P4", P4, "D5", 18.80, look="inkg", fit=(1.0, 1.10, 0.60, 0.48), life=1.1, fx=(FO(110, 0.34, 0.6),))]
    PG["D1"] = Page("D1", pd, fr(P0, 0.80, -2.0, 60, -40), [(16.13, 16.42, fr(P0, 0.98, 0.0), "expo"), whipk(16.85, fr(P1, 1.18, 2.0)), whipk(17.57, fr(P2, 1.18, -2.0)),
                                                         whipk(18.30, (960, 545, 0.97, 0.0)), whipk(19.01, fr(P4, 1.02, -1.0), 0.10, 0.09)],
                    sfx=[dict(L=A9["what"], x=590, y=720, t0=tl.LYR["what"], t1=16.72, rot=-6, s=0.80)],
                    hits=[(16.13, 1.5), (16.85, 1.0), (17.57, 1.0), (18.30, 1.1), (19.01, 1.3)])
    # ---------------------------------------------------------------- the crowd 22.86 - 23.81
    SP = [(40, 36), (1880, 36), (1880, 1044), (40, 1044)]
    PG["DX"] = Page("DX", [Pn("S", SP, "D10", 22.86, look="inkg", fit=(1.0, 1.10, 0.5, 0.55), life=0.95, fx=(FO(90, 0.40, 0.55),), brk=dict(look="raw", s=1.10, t=0.05, px=7))],
                    fr(SP, 0.90), [(22.86, 23.15, fr(SP, 1.0), "expo")], hits=[(22.86, 1.0)])
    # ---------------------------------------------------------------- drop page 3: the cafe 23.81 - 27.65
    LA = [(40, 40), (1120, 40), (1040, 1240), (40, 1300)]; LB = [(1180, 40), (2360, 40), (2360, 560), (1150, 600)]; LC = [(1146, 660), (2360, 620), (2360, 1000), (1120, 1040)]
    LD = [(1100, 1100), (2360, 1060), (2360, 1640), (1060, 1680)]; LE = [(40, 1360), (1000, 1300), (1020, 2060), (40, 2060)]; LF = [(40, 2120), (2360, 2120), (2360, 2900), (40, 2980)]
    pl = [Pn("A", LA, "W1", 23.81, fit=(1.05, 1.12, 0.5, 0.44), life=0.72, fx=(FO(100, 0.42, 0.55),)),
          Pn("B", LB, "L2", 24.53, fit=(1.0, 1.08, 0.5, 0.5), life=0.3, ent=(900, 0, 4, 1.0), fx=(("speed", -12, 55, 0.5, INKC),)),
          Pn("C", LC, "L3", 24.79, fit=(1.0, 1.06, 0.45, 0.45), life=0.46, ent=(900, 0, -3, 1.0)),
          Pn("D", LD, "L4", 25.25, fit=(1.0, 1.08, 0.45, 0.5), life=0.72, ent=(900, 200, 3, 1.0), fx=(("speed", 8, 45, 0.45, INKC),)),
          Pn("E", LE, "L5", 25.97, look="inkg", fit=(1.0, 1.06, 0.58, 0.42), life=0.73, ent=(-900, 0, -4, 1.0), fx=(FO(110, 0.34, 0.7),), brk=dict(look="inkg", s=1.08, t=0.04)),
          Pn("F", LF, "L6", 26.70, look="inkg", fit=(1.0, 1.08, 0.45, 0.5), life=0.95, ent=(0, 800, 0, 1.0))]
    PG["L"] = Page("L", pl, fr(LA, 0.86, 2.0), [(23.81, 24.08, fr(LA, 1.04, 0.0), "expo"), whipk(24.53, fr(LB, 1.12, -2.0)), whipk(24.79, fr(LC, 1.08, 1.0)),
                                               whipk(25.25, fr(LD, 1.10, -1.0)), whipk(25.97, fr(LE, 1.10, 1.5)), whipk(26.70, fr(LF, 1.03, 0.0), 0.10, 0.09)],
                   sfx=[dict(L=A9["go"], x=940, y=220, t0=23.81, t1=24.45, rot=-8, s=0.8), dict(L=A9["go"], x=1010, y=470, t0=24.05, t1=24.45, rot=6, s=0.8)],
                   hits=[(23.81, 1.0), (24.53, 0.8), (24.79, 1.2), (25.25, 0.9), (25.97, 1.0), (26.70, 1.3)])
    # ---------------------------------------------------------------- drop page 4: the spell 27.65 - 31.46
    SA = [(40, 40), (1500, 40), (1380, 820), (40, 900)]; SB = [(1560, 40), (2360, 40), (2360, 760), (1440, 800)]; SC = [(40, 960), (2360, 860), (2360, 1420), (40, 1480)]
    SD = [(40, 1540), (1240, 1540), (1240, 2560), (40, 2560)]; SE = [(1300, 1540), (2360, 1540), (2360, 1900), (1300, 1900)]; SF = [(1300, 1960), (2360, 1960), (2360, 2560), (1300, 2560)]
    ps_ = [Pn("A", SA, "S1", 27.65, look="inkg", fit=(1.0, 1.10, 0.42, 0.34), life=0.71, fx=(("speed", -35, 55, 0.5, INKC),)),
           Pn("B", SB, "S2", 28.36, look="inkg", fit=(1.0, 1.08, 0.5, 0.5), life=0.3, ent=(900, 0, 4, 1.0)),
           Pn("C", SC, "S3", 28.62, look="inkg", fit=(1.0, 1.06, 0.60, 0.40), life=0.46, ent=(-1200, 0, 0, 1.0)),
           Pn("D", SD, "S4", 29.08, look="inkg", fit=(1.0, 1.08, 0.5, 0.5), life=0.73, ent=(-900, 300, -3, 1.0)),
           Pn("E", SE, "S5", 29.81, look="inkg", fit=(1.0, 1.10, 0.5, 0.30), life=0.74, ent=(900, 0, 2, 1.0)),
           Pn("F", SF, "F6", 30.55, look="ink", fit=(1.0, 1.06, 0.5, 0.42), life=0.9, ent=(900, 200, 3, 1.0), swap=dict(t=30.55, dur=0.30, look="raw"), brk=dict(look="raw", s=1.10, t=0.05, px=7), rate=0.8)]
    def spell_extra(canvas, C, t, z):                      # the borrowed name, struck out; his real title stamped over it
        cap = A9["c_name"]; x, y = 1330, 2250
        if t >= 30.72:
            q = xf(C, [(x + cap["w"] / (2 * K), y + cap["h"] / (2 * K))])[0]; cap_draw(canvas, cap, t, 30.72, 99, q[0], q[1], z, -2)
            if t >= 31.00:
                u = out_cubic((t - 31.00) / 0.12); a = xf(C, [(x - 20, y + cap["h"] / (2 * K) + 14)])[0]; b = xf(C, [(x + cap["w"] / K + 10, y + cap["h"] / (2 * K) - 22)])[0]
                cv2.line(canvas, (int(a[0]), int(a[1])), (int(lerp(a[0], b[0], u)), int(lerp(a[1], b[1], u))), CRIM, max(3, int(16 * z * K)), cv2.LINE_AA)
        if t >= 31.12:
            e = out_expo((t - 31.12) / 0.12); q = xf(C, [(1830, 2470)])[0]; pm, a = A9["title"]
            X.place(canvas, pm, a, q[0], q[1], z * lerp(1.5, 1.0, e) * (P(980) / a.shape[1]), -3, clamp((t - 31.12) / 0.04))
    PG["S"] = Page("S", ps_, fr(SA, 0.88, -2.0), [(27.65, 27.92, fr(SA, 1.05, 0.0), "expo"), whipk(28.36, fr(SB, 1.12, 2.0)), whipk(28.62, fr(SC, 1.04, 0.0)),
                                                whipk(29.08, fr(SD, 1.06, -1.0)), whipk(29.81, fr(SE, 1.12, 1.0)), whipk(30.55, fr(SF, 1.26, 0.0, 0, 30), 0.10, 0.09)],
                   sfx=[dict(L=A9["go"], x=2180, y=1640, t0=29.81, t1=30.50, rot=-8, s=0.7), dict(L=A9["go"], x=2250, y=1800, t0=30.05, t1=30.50, rot=6, s=0.7)],
                   hits=[(27.65, 1.0), (28.36, 0.7), (28.62, 1.1), (29.08, 0.9), (29.81, 0.8), (30.55, 1.4), (31.12, 0.5)], extra=spell_extra)
    # ---------------------------------------------------------------- outro page 31.46 - 40.55
    OA = [(40, 40), (1170, 40), (1170, 900), (40, 900)]; OB = [(1230, 40), (2360, 40), (2360, 900), (1230, 900)]; OC = [(40, 960), (1300, 960), (1300, 1640), (40, 1640)]
    OD = [(1360, 960), (2360, 960), (2360, 1640), (1360, 1640)]; OE = [(40, 1700), (1100, 1700), (1100, 2260), (40, 2260)]; OF = [(1160, 1700), (2360, 1700), (2360, 2260), (1160, 2260)]
    po = [Pn("A", OA, "O1a", 31.30, fit=(1.25, 1.32, 0.42, 0.45), life=2.0, rate=0.8),
          Pn("B", OB, "O1a", 31.30, fit=(1.25, 1.32, 0.42, 0.45), life=2.0, flip=True, rate=0.8,
             swap=dict(t=32.05, dur=0.95, shot="O1b", look="ink", mode="fade", fit=(1.9, 2.0, 0.36, 0.40), flip=True)),
          Pn("C", OC, "O2", 33.46, fit=(1.0, 1.08, 0.5, 0.5), life=1.9, ent=(-700, 0, -2, 1.0), edur=0.3),
          Pn("D", OD, "O3", 35.39, fit=(1.0, 1.06, 0.5, 0.45), life=1.9, ent=(700, 0, 2, 1.0), edur=0.3, wipe=(36.26, 0.85)),
          Pn("E", OE, "O4", 37.27, fit=(1.0, 1.08, 0.48, 0.42), life=1.9, ent=(-700, 0, -2, 1.0), edur=0.3),
          Pn("F", OF, "O5", 39.18, fit=(1.0, 1.06, 0.5, 0.40), life=1.4, ent=(700, 0, 2, 1.0), edur=0.3)]
    AB = OA + OB
    PG["O"] = Page("O", po, fr(AB, 0.98), [(31.46, 32.0, fr(AB, 1.05), "out"), (33.30, 33.66, fr(OC, 1.22, -1.0, 0, 60), "io"), (35.22, 35.58, fr(OD, 1.22, 1.0, 0, 60), "io"),
                                        (37.10, 37.46, fr(OE, 1.22, -1.0, 0, 50), "io"), (39.02, 39.38, fr(OF, 1.20, 0.5), "io"), (39.70, 40.55, (1760, 1980, 0.26, -4.0), "smooth")],
                   caps=[dict(cap="c_mirror", x=70, y=760, t0=32.20, t1=33.40, s=1.45), dict(cap="c_recog", x=80, y=1520, t0=33.60, t1=35.30),
                         dict(cap="c_gone", x=1400, y=1520, t0=35.14, t1=37.16), dict(cap="c_mask", x=80, y=2170, t0=36.90, t1=39.10)],
                   hits=[(31.46, 0.5), (33.46, 0.35), (35.39, 0.35), (37.27, 0.35), (37.62, 0.5), (39.18, 0.3)], creep=0.05)


# ======================================================================== the opening (kept from the cut the user liked; new type, no glitch)
def scene_intro(t):
    if t < 0.81: canvas = cv2.convertScaleAbs(render_shot(SH["ST"], t), alpha=0.50)
    else:
        page = R8.intro_page(t); cC = np.asarray(PTS(R8.PAN["C"]["pts"])).mean(0); drift = 0.012 * math.sin(t * 0.9)
        s_ = 1.0 + 0.03 * smooth((t - 0.81) / 4.0); cx_, cy_ = W / 2, H / 2; rot = 0.6 * math.sin(t * 0.7)
        if t >= 5.02:
            u = clamp((t - 5.02) / 1.09) ** 2.6; s_ = lerp(s_, 2.35, u); cx_ = lerp(W / 2, cC[0], smooth(u * 1.4)); cy_ = lerp(H / 2, cC[1] - 80 * K, smooth(u * 1.4)); rot = lerp(rot, -2.0, u)
        M = cv2.getRotationMatrix2D((float(cx_), float(cy_)), rot, s_ + drift); M[0, 2] += W / 2 - cx_; M[1, 2] += H / 2 - cy_
        canvas = cv2.warpAffine(page, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=PAGEC)
    q, a1, a2 = A9["c_q"], A9["c_a1"], A9["c_a2"]
    cap_draw(canvas, q, t, 0.30, 2.42, P(86) + q["w"] / 2, P(520) + q["h"] / 2, 1.0, -1.0)
    cap_draw(canvas, a1, t, 2.45, 4.02, P(96) + a1["w"] / 2, P(486) + a1["h"] / 2, 1.0, -1.5)
    cap_draw(canvas, a2, t, 4.05, 5.90, P(70) + a2["w"] / 2, P(500) + a2["h"] / 2, 1.0, -1.5)
    if t >= 5.80: canvas = cv2.addWeighted(canvas, 1.0, np.full_like(canvas, 255), smooth((t - 5.80) / 0.31), 0)
    return canvas


def v_face(t):                                    # 8.74-9.46: FACE, flat and heavy, behind the skull cut-out
    canvas = R8.tone_field((28, 18, 120), (8, 6, 30), 9.0, (0.05, 0.95), (0.7, 0.7))
    dt = t - 8.74; e = out_expo(dt / 0.16); pm, a = A9["face"]
    X.place(canvas, pm, a, P(540) + (1 - e) * P(-500), P(560), (P(940) / a.shape[1]) * (1 + 0.03 * dt), -3, clamp(dt / 0.04))
    img, m = R8.srcm("V2", t, "duo_bone"); u = out_back(clamp(dt / 0.26), 1.6)
    R8.stick_full(canvas, img, m, px=0, shadow=(16, -14, 20, 0.75), dx=lerp(P(900), P(560), u), dy=P(20), rot=lerp(8, 2, u))
    return canvas


def v_f2f(t):                                     # 9.46-10.43: face to face, split
    dt = t - 9.46; u = out_back(clamp(dt / 0.24), 1.3); swap = t >= 9.94
    L = R8.tone_field((150, 120, 20), (60, 30, 6), 8.0, (0.1, 0.9), (1, 0.3)); R = R8.tone_field((30, 20, 150), (10, 6, 50), 8.0, (0.1, 0.9), (-1, 0.3))
    img, m = R8.srcm("PF", t, "raw", zm=1.05); R8.stick_full(L, img, m, px=6, col=WHITE, shadow=(10, 12, 12, 0.6), dx=-P(330), dy=P(30), s=0.92)
    sk = R8.src("SKe", t, "duo_red", zm=1.25); sk = cv2.addWeighted(sk, 1.0, R, 0.35, 0); R = cv2.addWeighted(R, 0.35, sk, 0.9, 0)
    sx = (1 - u) * W * 0.62; off = P(40) * smooth((t - 9.94) / 0.10); xa, xb = W * 0.56 - off, W * 0.44 - off
    pl = [(-sx, 0), (xa - sx, 0), (xb - sx, H), (-sx, H)]; pr = [(xa + sx, 0), (W + sx, 0), (W + sx, H), (xb + sx, H)]
    canvas = np.empty((H, W, 3), np.uint8); canvas[:] = (8, 8, 10)
    X.panel(canvas, X.warp_to(L, 1.0, 0, -sx, 0, border=cv2.BORDER_REPLICATE), pl, border=0)
    X.panel(canvas, X.warp_to(R, 1.0, 0, sx, 0, border=cv2.BORDER_REPLICATE), pr, border=0)
    cv2.line(canvas, (int(xa), 0), (int(xb), H), WHITE, max(2, int(12 * K)), cv2.LINE_AA)
    for i, tt in enumerate((9.46, 9.60, 9.74)):
        if t >= tt:
            e = out_back(clamp((t - tt) / 0.12), 2.2); X.place(canvas, *A9["f2f"][i], W * 0.5 + P((-34, 0, 34)[i]), H * 0.5 + P((i - 1) * 180), e * 0.95, -6)
    return canvas


# ======================================================================== rebirth 19.96 - 22.86 (light -> circle -> his eye -> the dead), inked
def eye9(t): return R8.src("R2", t, "ink")
def ghosts9(t): return R8.src("D9", t, "inkg")


def rebirth(t):
    if t < 20.40:
        c = R8.src("D6", t, "inkg"); fl = X.focus_lines(H, W, W * 0.5, H * 0.30, X.on2(t), n=90, r_in=0.22); X.paint(c, INKC, fl * 0.45)
        c = cv2.addWeighted(c, 1.0, np.full_like(c, 255), smooth((t - 20.10) / 0.30), 0)
    elif t < SH["R2"]["t0"]:
        c = R8.src("R1", t, "duo_gold"); c = cv2.addWeighted(c, 1.0, np.full_like(c, 255), 1 - smooth((t - 20.40) / 0.35), 0); R7.ring_on_circle(c, t)
    elif t < SH["R2"]["t0"] + 0.50:
        ca = R4.reinc_circle(t); bx, by, bz = R4.to_screen(SH["R2"], t, ZERO_ACC, 0.545, 0.36)
        c = circle_match(R8.src("R1", t, "duo_gold"), eye9(t), ca, (bx, by, 0.05 * W * bz), (t - SH["R2"]["t0"]) / 0.50, ring=WHITE); R7.ring_on_circle(c, t)
    elif t < 21.95: c = eye9(t)
    elif t < 22.27:
        ex, ey, _ = R4.to_screen(SH["R2"], t, ZERO_ACC, 0.545, 0.36); c = iris_through(eye9(t), ghosts9(t), ex, ey, (t - 21.95) / 0.32, ring=WHITE)
    else: c = ghosts9(t)
    return splash(c)


def splash(c, m=30):
    """a full-page panel: black gutter and a white border around the frame."""
    m = int(m * K); b = max(2, int(8 * K)); c[:m] = PAGEC; c[H - m:] = PAGEC; c[:, :m] = PAGEC; c[:, W - m:] = PAGEC
    cv2.rectangle(c, (m, m), (W - m, H - m), WHITE, b, cv2.LINE_AA); return c


def push(A_, B_, u, dx, dy):
    e = X.ease_io(u, 3); out = np.empty_like(A_); out[:] = PAGEC
    sh = lambda img, ox, oy: cv2.warpAffine(img, np.float32([[1, 0, ox], [0, 1, oy]]), (W, H), borderMode=cv2.BORDER_CONSTANT, borderValue=PAGEC)
    a = sh(A_, -e * W * dx, -e * H * dy); b = sh(B_, (1 - e) * W * dx, (1 - e) * H * dy)
    return np.maximum(a, b)


# ======================================================================== tag + card
def scene_tag(t):
    c = np.empty((H, W, 3), np.uint8); c[:] = PAGEC; dt = t - 40.55
    pts = PTS([(70, 70), (1850, 70), (1850, 700), (70, 700)]); z = 1.0 + 0.02 * dt
    cont = R8.fit_into(R8.base("T1", t, "inkg"), pts, 1.0 + 0.012 * dt, 0.5, 0.40)
    k = smooth((t - 44.40) / 0.45)                 # "...not on the inside": the skull under his face
    if k > 0.01:
        sk = R8.fit_into(R8.base("S5", SH["S5"]["t0"] + 0.25, "inkg"), pts, 1.0 + 0.03 * k, 0.5, 0.27); cont = cv2.addWeighted(cont, 1 - k, sk, k, 0)
    X.panel(c, cont, pts, border=max(2, int(8 * K)), bcol=WHITE)
    for cap, a, b in (("c_t1", 40.80, 41.92), ("c_t2", 41.92, 43.90), ("c_t3", 43.90, 45.14)):
        cp = A9[cap]; cap_draw(c, cp, t, a, b, P(96) + cp["w"] / 2, P(640) + cp["h"] / 2, 1.0, -1.0)
    return cv2.convertScaleAbs(c, alpha=clamp(dt / 0.35) * clamp((45.18 - t) / 0.10))


# ======================================================================== dispatch + motion blur
MB_LEGACY = [(0.79, 1.14), (2.72, 3.07), (4.65, 5.45), (5.45, 6.11), (8.72, 9.04), (9.44, 9.78), (9.92, 10.06), (21.08, 21.62), (21.93, 22.29)]
PAGES = [("V", 10.43, 16.13), ("D1", 16.13, 19.96), ("DX", 22.86, 23.81), ("L", 23.81, 27.65), ("S", 27.65, 31.46), ("O", 31.46, 40.55)]
PUSH = [(19.96, 0.09, 0.09, 0, 1), (22.86, 0.08, 0.08, 1, 0), (23.81, 0.08, 0.08, -1, 0), (27.65, 0.08, 0.08, 0, 1), (31.46, 0.10, 0.14, 1, 0)]


def scene(t):
    if t < tl.LOGO_T[0]: return scene_intro(t)
    if t < tl.LOGO_T[4]: return R2.scene_logo(t, 0)
    if t < 8.74: return R8.v_skull(t)
    if t < 9.46: return v_face(t)
    if t < 10.43: return v_f2f(t)
    if t < 19.96: return PG["V"].render(t) if t < 16.13 else PG["D1"].render(t)
    if t < 22.86: return rebirth(t)
    for key, a, b in PAGES[2:]:
        if a <= t < b: return PG[key].render(t)
    if t < tl.CARD_T: return scene_tag(t)
    return R7.scene_card(t, 0)


def render_t(t):
    if 15.30 <= t < 16.13:
        a = PG["V"].render(t); cp = A9["c_ask"]; cap_draw(a, cp, t, tl.LYR["asking"], 15.97, P(250) + cp["w"] / 2, P(790), 1.25, -3.0)
        if t < 15.88: return a                     # ... then the dive through his eye into the drop
        return iris_through(a, PG["D1"].render(t), W * 0.5, H * 0.5, (t - 15.88) / 0.25, ring=WHITE)
    for tc, pre, post, dx, dy in PUSH:
        if tc - pre <= t < tc + post:
            eps = 1e-4; return push(scene(tc - eps - (tc - t if t < tc else 0)), scene(max(t, tc)), (t - (tc - pre)) / (pre + post), dx, dy)
    c = scene(t)
    if 40.20 <= t < 40.55: c = cv2.convertScaleAbs(c, alpha=1 - smooth((t - 40.20) / 0.33))
    return c


def moving(t):
    for a, b in MB_LEGACY:
        if a <= t < b: return True
    if 15.86 <= t < 16.15: return True
    for tc, pre, post, _, _ in PUSH:
        if tc - pre - 0.02 <= t < tc + post + 0.02: return True
    for key, a, b in PAGES:
        if a <= t < b: return PG[key].moving(t)
    return False


SHUT = 0.62


def mb_plan(t):
    """(samples, per-sample smear vector in px) for the frame at t; (1, None) when nothing moves."""
    if not moving(t): return 1, None
    h = SHUT / 2 / FPS; d = np.zeros(2); zr = 0.0
    for tc, pre, post, dx, dy in PUSH:
        if tc - pre - 0.02 <= t < tc + post + 0.02:
            u = lambda tt: X.ease_io((tt - (tc - pre)) / (pre + post), 3); k = u(t + h) - u(t - h); d = np.array([k * W * dx, k * H * dy]); break
    else:
        if not (15.86 <= t < 16.15):
            for key, a, b in PAGES:
                if a <= t < b:
                    pg = PG[key]; c1, c2, c = pg.cam(t - h), pg.cam(t + h), pg.cam(t); p = [(c[0], c[1])]
                    d = xf(cam3(c2), p)[0] - xf(cam3(c1), p)[0]; zr = abs(c2[2] / c1[2] - 1) * math.hypot(W, H) / 2
    mag = float(np.hypot(*d)) + zr; n = int(clamp(math.ceil(mag / (9 * K)), 5, 14))
    if 15.86 <= t < 16.15: n = 10
    if any(a <= t < b for a, b in MB_LEGACY): n = 10
    for key, a, b in PAGES:
        if a <= t < b and any(p.ent != (0, 0, 0, 1.0) and -0.02 <= t - p.t0 < p.edur * 0.7 for p in PG[key].panels): n = max(n, 12)
    return n, (d / (n - 1) if np.hypot(*d) > max(3.0, 1.5 * zr) else None)


def smear(img, v):
    L = float(np.hypot(*v))
    if L < 2.5: return img
    n = int(math.ceil(L)) | 1; k = np.zeros((n, n), np.float32); c = n // 2; ux, uy = v / L
    cv2.line(k, (int(round(c - ux * L / 2)), int(round(c - uy * L / 2))), (int(round(c + ux * L / 2)), int(round(c + uy * L / 2))), 1.0, 1)
    return cv2.filter2D(img, -1, k / k.sum(), borderType=cv2.BORDER_REPLICATE)


def frame_at(n):
    t = n / FPS; ns, v = mb_plan(t)
    if ns > 1:
        acc = np.zeros((H, W, 3), np.float32)
        for i in range(ns):
            fr_ = render_t(max(0.0, t + (i / (ns - 1) - 0.5) * SHUT / FPS)); acc += fr_ if v is None else smear(fr_, v)
        canvas = (acc / ns + 0.5).astype(np.uint8)
    else: canvas = render_t(t)
    kw = dict(grain=0.05, glow0=0.05, vig=0.30, ca=False, streak=False, hal=False)
    if tl.LOGO_T[0] <= t < tl.LOGO_T[4] or t >= tl.CARD_T: kw.update(glow0=0.0, vig=0.0, grain=0.04)
    canvas = R7.post7(canvas, t, ZERO_ACC, n, **kw)
    R7.signature(canvas, t)
    return canvas


def worker(args):
    wi, n0, n1 = args; out = f"{ROOT}/out/{MODE}9_part{wi}.mp4"
    enc = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709",
           "-color_trc", "bt709", "-color_range", "tv", "-c:v", "libx264", "-preset", "medium" if MODE == "final" else "veryfast",
           "-crf", "15" if MODE == "final" else "20", "-threads", "2", out]
    p = subprocess.Popen(enc, stdin=subprocess.PIPE)
    for n in range(n0, n1): p.stdin.write(frame_at(n).tobytes())
    p.stdin.close(); p.wait(); return out


if __name__ == "__main__":
    T0 = float(sys.argv[2]) if len(sys.argv) > 3 else 0.0; T1 = float(sys.argv[3]) if len(sys.argv) > 3 else tl.END
    os.makedirs(f"{ROOT}/out", exist_ok=True)
    n0, n1 = int(round(T0 * FPS)), int(round(T1 * FPS)); NW = 4
    CH = max(1, int(FPS * 1.0)); chunks = [(n, min(n1, n + CH)) for n in range(n0, n1, CH)]
    jobs = [(i, a, b) for i, (a, b) in enumerate(chunks)]
    with mp.Pool(NW, initializer=setup9, maxtasksperchild=5) as pool: parts = pool.map(worker, jobs, chunksize=1)   # recycle workers: caches stay bounded
    with open(f"{ROOT}/out/{MODE}9_parts.txt", "w") as f:
        for p in parts: f.write(f"file '{p}'\n")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{ROOT}/out/{MODE}9_parts.txt", "-c", "copy", f"{ROOT}/out/{MODE}9_video.mp4"], check=True)
    for p in parts: os.remove(p)
    print("wrote", f"{ROOT}/out/{MODE}9_video.mp4", n1 - n0, "frames")
