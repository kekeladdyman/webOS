"""V2 renderer. usage: render2.py [draft|final] [t_start t_end]  -> out/<mode>2_video.mp4"""
import subprocess, multiprocessing as mp
from r2core import *

SH = tl.BY
A = None          # assets (per worker)
OPEN, MID, CLOSE = tl.DLG_OPEN_T, tl.DLG_MID_T, tl.DLG_CLOSE_T


# ====================================================================== assets
class Assets:
    def __init__(s):
        k = K
        # ---- film reel (cold open)
        s.pw = int(W * 0.80) // 2 * 2; s.ph = int(s.pw * 9 / 16) // 2 * 2
        fi = "IMFellItalic.ttf"
        s.ink = {w: tmask(w, fi, 104 * k, vcrop=False) for w in ("All", "I", "wanted", "Nothing", "more.")}
        s.ink["was"] = tmask("was", fi, 92 * k, vcrop=False); s.ink["peace."] = tmask("peace.", fi, 230 * k, vcrop=False)
        s.kanji_peace = tmask("平穏", "ZenAntique.ttf", 120 * k, vertical=True)
        sp = H // 5; s.sp = sp
        base = np.zeros((H + sp, W, 3), np.uint8); base[:] = (16, 13, 12)
        side = (W - s.pw) // 2; hw, hh = int(side * 0.36), int(sp * 0.46)
        hole = np.zeros((H + sp, W), np.uint8)
        for y in range(-sp, H + 2 * sp, sp):
            for xc in (side // 2, W - side // 2):
                cv2.rectangle(hole, (xc - hw // 2, y + sp // 2 - hh // 2), (xc + hw // 2, y + sp // 2 + hh // 2), 255, -1)
        hole = cv2.GaussianBlur(hole, (0, 0), 3 * k + 0.5); hole = np.clip(hole.astype(np.float32) * 1.6, 0, 255).astype(np.uint8)
        glow = cv2.GaussianBlur(hole, (0, 0), 14 * k)
        lightc = np.zeros_like(base); lightc[:] = (205, 232, 246)
        base = cv2.add(base, premult(lightc, cv2.max(hole, (glow * 0.35).astype(np.uint8))))
        et = tmask("DMDP  ·  5247  ·  SAFETY FILM  ·  REEL 00  ·  THE PAST   ", "SpaceMono.ttf", 15 * k, tracking=4 * k)
        et = cv2.rotate(et, cv2.ROTATE_90_COUNTERCLOCKWISE); pm, a = layer(et, fill=(70, 150, 215))
        for y in range(0, H + sp, et.shape[0] + int(30 * k)):
            for xc in (int(side * 0.86), W - int(side * 0.14) - et.shape[1]):
                comp_pm(base, pm, a, 0.55, xc, y)
        s.film_base = base; s.side = side
        yy, xx = np.mgrid[0:s.ph, 0:s.pw].astype(np.float32)
        r2 = ((xx - s.pw / 2) / (s.pw / 2)) ** 2 + ((yy - s.ph / 2) / (s.ph / 2)) ** 2
        v = np.clip(1.0 - 0.42 * np.clip(r2 - 0.2, 0, None) ** 1.2, 0.3, 1.0)
        s.film_vig = cv2.merge([(v * 255).astype(np.uint8)] * 3)
        rng = np.random.default_rng(11)
        nz = cv2.GaussianBlur(rng.random((H // 8, W // 8)).astype(np.float32), (0, 0), 5)
        nz = (nz - nz.min()) / (nz.max() - nz.min()); s.burn = cv2.resize(nz, (W, H), interpolation=cv2.INTER_CUBIC)
        # ---- micro type helper (the title is the official logo footage, nothing custom)
        mono = lambda t, sz=16: layer(tmask(t, "SpaceMono.ttf", sz * k, tracking=3.2 * k), fill=BONE)
        s.mono = mono; s.logo_steps = None
        # ---- lyric type
        sc_ = "MrDafoe.ttf"; se = "InstrumentSerif.ttf"; si = "InstrumentSerifItalic.ttf"
        sh = (9 * k, 0.55, 0, 5 * k)
        s.script = {}
        for key, txt, sz in (("aint_big", "Ain’t no", 250), ("aint", "ain’t no", 175), ("high", "high", 150), ("low", "low", 150), ("wide", "wide", 150),
                             ("baby", "baby", 170), ("nomatter", "no matter", 130), ("dontworry", "don’t worry, baby", 124),
                             ("justcall", "just call my name", 94), ("youdont", "you don’t have to", 104), ("ifyou", "if you need me,", 118)):
            s.script[key] = layer(tmask(txt, sc_, sz * k), fill=GOLD, stroke=((20, 8, 34), 3 * k), shadow=sh)
        s.script["ifyou"] = layer(tmask("if you need me,", sc_, 124 * k), fill=BONE, stroke=((20, 8, 34), 4 * k), shadow=sh)
        s.L_mount = letters("MOUNTAIN", se, 310 * k, tracking=8 * k); s.L_valley = letters("VALLEY", se, 250 * k, tracking=58 * k)
        s.L_river = letters("RIVER", si, 330 * k, tracking=30 * k)
        s.enough_v = layer(tmask("ENOUGH", "GrenzeGotisch.ttf", 330 * k, wght=900, tracking=4 * k), fill=RED, stroke=(BONE, 3 * k), extrude=(10, 1.1 * k, 1.1 * k, (18, 6, 40)))
        dk = ((20, 10, 26), 4 * k)
        s.callme = layer(tmask("CALL ME", se, 220 * k, tracking=10 * k), fill=BONE, stroke=dk, shadow=sh)
        s.where = layer(tmask("WHERE YOU ARE", se, 150 * k, tracking=6 * k), fill=BONE, stroke=dk, shadow=sh)
        s.L_howfar = letters("HOW FAR", se, 250 * k, tracking=10 * k)
        s.illbe = [layer(tmask(w, si, 190 * k), fill=BONE, stroke=dk, shadow=sh) for w in ("I’ll", "be", "there")]
        s.hurry = layer(tmask("IN A HURRY", "Shrikhand.ttf", 210 * k, tracking=2 * k), grad=(BONE, GOLD), extrude=(8, 1.2 * k, 1.0 * k, DEEP))
        s.worry = layer(tmask("WORRY", se, 250 * k, tracking=8 * k), fill=BONE, stroke=dk, shadow=sh)
        # ---- location + micro
        s.shinjuku = tmask("新宿", "DelaGothicOne.ttf", 250 * k, vertical=True, line_gap=-30 * k)
        s.loc_lab = cv2.rotate(tmask("SHINJUKU   ·   TOKYO   ·   PRESENT DAY", "SpaceMono.ttf", 18 * k, tracking=6 * k), cv2.ROTATE_90_COUNTERCLOCKWISE)
        s.loc_co = mono("35.6938° N   139.7034° E", 15)
        s.apart = mono("ONE  DEATH  APART", 17)
        s.lab_other = (layer(tmask("異世界", "ZenAntique.ttf", 30 * k, tracking=4 * k), fill=BONE), mono("ANOTHER WORLD", 15))
        s.lab_shin = (layer(tmask("新宿", "ZenAntique.ttf", 30 * k, tracking=4 * k), fill=BONE), mono("SHINJUKU", 15))
        s.card_labels = {"C2": mono("EP.01  ·  02:34  ·  THE CORPSE GOD", 14), "C4": mono("EP.01  ·  08:34  ·  KORMINE", 14),
                         "C6": mono("EP.01  ·  03:25  ·  THE CALAMITY CRUSHER", 14), "P": mono("EP.05  ·  05:27  ·  THE BAR", 14)}
        s.card_idx = {"C2": mono("N° 01 / 03", 14), "C4": mono("N° 02 / 03", 14), "C6": mono("N° 03 / 03", 14), "P": mono("N° 00", 14)}
        s.frame_cache = {}
        # ---- polaroids
        s.iw, s.ih = int(600 * k), int(450 * k); s.pb = int(28 * k); s.pbb = int(104 * k); s.ptop = int(70 * k)
        hand = "PermanentMarker.ttf"
        s.names = [tmask(t, hand, sz * k) for t, sz in (("the kids", 58), ("Misaki", 64), ("Takumi", 64), ("me.", 70))]
        rngp = np.random.default_rng(5)
        pw_, ph_ = s.iw + 2 * s.pb, s.ih + s.pb + s.pbb
        paper = np.clip(rngp.normal(0, 3.0, (ph_, pw_, 1)) + np.array([[[232, 238, 242]]], np.float32), 0, 255).astype(np.uint8)
        s.paper = paper
        sm_ = np.zeros((ph_ + int(120 * k), pw_ + int(120 * k)), np.uint8); o = int(60 * k); sm_[o:o + ph_, o:o + pw_] = 255
        s.pshadow = cv2.GaussianBlur(sm_, (0, 0), 20 * k)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); r = np.hypot((xx - W * 0.5) / W, (yy - H * 0.48) / H)
        tb = np.clip(1.0 - r * 1.55, 0.0, 1.0)[..., None]
        s.table = np.clip(np.array([[[20, 14, 20]]], np.float32) + tb * np.array([[[40, 30, 46]]], np.float32) + rngp.normal(0, 2.2, (H, W, 1)), 0, 255).astype(np.uint8)
        # ---- dialogue type
        s.d_prot = [layer(tmask(w, fi, 112 * k, vcrop=False), fill=BONE, shadow=sh) for w in ("I’ll", "protect", "you,")]
        s.d_nmw = [layer(tmask(w, "GrenzeGotisch.ttf", 150 * k, wght=800, vcrop=False), fill=RED, stroke=(BONE, 2 * k), shadow=sh) for w in ("no", "matter", "what.")]
        s.d_close = [[layer(tmask(w, fi, 74 * k, vcrop=False), fill=BONE, stroke=((20, 10, 26), 3 * k), shadow=sh) for w in ln] for ln in (("It", "seems", "this", "land"), ("I’ve", "arrived", "in", "is"))]
        s.peaceful = layer(tmask("peaceful.", si, 300 * k), fill=GOLD, stroke=((20, 8, 34), 4 * k), shadow=(12 * k, 0.5, 0, 6 * k))
        s.kanji_peace_w = layer(tmask("平穏", "ZenAntique.ttf", 150 * k, vertical=True), fill=BONE, stroke=((20, 10, 26), 4 * k), shadow=sh)
        # ---- chorus type
        sk = "Shrikhand.ttf"; ex = lambda n: (n, 1.3 * k, 1.3 * k, DEEP)
        s.c_aint = layer(tmask("AIN’T", sk, 430 * k), grad=(BONE, GOLD), stroke=(DEEP, 4 * k), extrude=ex(14))
        s.c_no = [layer(tmask(c, sk, 640 * k), grad=(BONE, GOLD), stroke=(DEEP, 5 * k), extrude=ex(16)) for c in "NO"]
        s.c_mount = layer(tmask("MOUNTAIN", sk, 262 * k, tracking=2 * k), grad=(GOLD, BONE), stroke=(DEEP, 4 * k), extrude=ex(14))
        s.c_high = layer(tmask("HIGH", sk, 520 * k), grad=(BONE, GOLD), stroke=(DEEP, 5 * k), extrude=ex(16))
        s.c_enough = layer(tmask("ENOUGH", "GrenzeGotisch.ttf", 470 * k, wght=900, tracking=4 * k), fill=RED, stroke=(BONE, 4 * k), extrude=(12, 1.2 * k, 1.2 * k, (14, 4, 30)))
        s.c_en_l = layer(tmask("ENO", "GrenzeGotisch.ttf", 470 * k, wght=900, tracking=4 * k), fill=RED, stroke=(BONE, 4 * k), extrude=(12, 1.2 * k, 1.2 * k, (14, 4, 30)))
        s.c_en_r = layer(tmask("UGH", "GrenzeGotisch.ttf", 470 * k, wght=900, tracking=4 * k), fill=RED, stroke=(BONE, 4 * k), extrude=(12, 1.2 * k, 1.2 * k, (14, 4, 30)))
        # ---- post
        rng = np.random.default_rng(7); s.noise = []
        for _ in range(6):
            nz = rng.normal(128, 26, (H // 2 + 1, W // 2 + 1)).astype(np.float32)
            nz = np.clip(cv2.resize(nz, (W, H), interpolation=cv2.INTER_CUBIC), 0, 255).astype(np.uint8); s.noise.append(cv2.merge([nz, nz, nz]))
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r2 = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
        v = np.clip(1.0 - 0.30 * np.clip(r2 - 0.25, 0, None) ** 1.3, 0.35, 1.0); s.vig = cv2.merge([(v * 255).astype(np.uint8)] * 3)


def word_layer(L, color, offs, wmul=1.0, hmul=1.0):
    """compose animated letters into one premultiplied layer. offs[i] = (dx, dy, alpha)."""
    ls, (tw, th) = L
    pad = int(th * 0.5); cw, ch = int(tw * wmul) + 2 * pad, int(th * hmul) + 2 * pad
    a = np.zeros((ch, cw), np.uint8)
    for (m, x), (dx, dy, al) in zip(ls, offs):
        if al <= 0.01: continue
        xi, yi = int(round(pad + x + dx)), int(round(pad + dy)); h, w = m.shape
        xa, ya = max(0, xi), max(0, yi); xb, yb = min(cw, xi + w), min(ch, yi + h)
        if xa >= xb or ya >= yb: continue
        seg = m[ya - yi:yb - yi, xa - xi:xb - xi]
        if al < 0.999: seg = cv2.convertScaleAbs(seg, alpha=al)
        a[ya:yb, xa:xb] = cv2.max(a[ya:yb, xa:xb], seg)
    col = np.empty((ch, cw, 3), np.uint8); col[:] = color
    return premult(col, a), a


def with_shadow(pm, a, sigma, op, dy):
    sm = cv2.GaussianBlur(a, (0, 0), sigma); sm = np.roll(sm, int(dy), 0); sm = cv2.convertScaleAbs(sm, alpha=op)
    inv = cv2.merge([255 - a] * 3); z = np.zeros_like(pm)
    na = cv2.add(a, cv2.multiply(sm, 255 - a, scale=1 / 255.0))
    return pm, na      # shadow has black colour -> premult colour unchanged, only alpha grows


# ====================================================================== generic bits
def full(t, acc):
    canvas = np.zeros((H, W, 3), np.uint8)
    act = [s for s in tl.SHOTS if s["t0"] <= t < s["t1"] and s["mode"] == "full"]
    for i, s in enumerate(act):
        img = render_shot(s, t, acc)
        a = clamp((t - s["t0"]) / s["fin"]) if s["fin"] > 0 else 1.0
        if i == len(act) - 1 and s["fout"] > 0: a *= clamp((s["t1"] - t) / s["fout"])
        canvas = img if a >= 0.999 else cv2.addWeighted(canvas, 1 - a, img, a, 0) if a > 0.001 else canvas
    return canvas


def backdrop(img, dim=0.27, tint=(1.08, 0.94, 1.0)):
    sm = cv2.resize(img, (W // 24, H // 24), interpolation=cv2.INTER_AREA)
    sm = cv2.GaussianBlur(sm, (0, 0), 2.2)
    bg = cv2.resize(sm, (W, H), interpolation=cv2.INTER_CUBIC).astype(np.float32) * dim * np.array(tint, np.float32)
    return np.clip(bg + 5, 0, 255).astype(np.uint8)


def plus_markers(canvas, R, t, seed=0.0, alpha=0.38, cam=1.0):
    col = tuple(int(c * alpha) for c in BONE); L = int(7 * K) + 2
    for i in range(6):
        for j in range(4):
            x = (i + 0.5 + 0.3 * hrand(i, j, seed)) * W / 6 - W / 2; y = (j + 0.5 + 0.3 * hrand(j, i, seed + 3)) * H / 4 - H / 2
            p = np.array([x * 1.5, y * 1.5, 520.0 * K]) @ R.T; f = 1.7 * W; z = f + p[2]
            sx, sy = int(W / 2 + cam * f * p[0] / z), int(H / 2 + cam * f * p[1] / z)
            cv2.line(canvas, (sx - L, sy), (sx + L, sy), col, 1, cv2.LINE_AA); cv2.line(canvas, (sx, sy - L), (sx, sy + L), col, 1, cv2.LINE_AA)


def frame_tex(cw, ch, label, idx):
    """thin outer frame with corner ticks + micro labels, as premultiplied texture bigger than the card."""
    mx, my = int(cw * 0.045) + int(8 * K), int(ch * 0.07) + int(8 * K); ex = int(46 * K)
    tw, th = cw + 2 * mx + 2 * ex, ch + 2 * my + 2 * ex
    a = np.zeros((th, tw), np.uint8); lw = max(1, int(round(1.6 * K)))
    x0, y0, x1, y1 = ex, ex, tw - ex - 1, th - ex - 1
    cv2.rectangle(a, (x0, y0), (x1, y1), 200, lw, cv2.LINE_AA)
    t_ = int(22 * K)
    for (x, y, sx, sy) in ((x0, y0, -1, -1), (x1, y0, 1, -1), (x1, y1, 1, 1), (x0, y1, -1, 1)):
        cv2.line(a, (x + sx * int(10 * K), y), (x + sx * (int(10 * K) + t_), y), 255, lw, cv2.LINE_AA)
        cv2.line(a, (x, y + sy * int(10 * K)), (x, y + sy * (int(10 * K) + t_)), 255, lw, cv2.LINE_AA)
    col = np.empty((th, tw, 3), np.uint8); col[:] = BONE; pm = premult(col, a)
    if label is not None: comp_pm(pm, label[0], label[1], 1.0, x0 + int(4 * K), y0 - label[1].shape[0] - int(5 * K)); a = cv2.max(a, cv2.max(pm[..., 0], pm[..., 2]))
    if idx is not None: comp_pm(pm, idx[0], idx[1], 1.0, x1 - idx[1].shape[1] - int(4 * K), y1 + int(7 * K)); a = cv2.max(a, cv2.max(pm[..., 0], pm[..., 2]))
    return pm, a


def card(canvas, img, R, cx, cy, cam=1.0, key=None, label=None, idx=None, frame_op=1.0, lroll=0.0, shadow=0.55):
    """floating bordered card: soft shadow, image plane with hairline edge, nearer thin outer frame."""
    ch, cw = img.shape[:2]
    sh = np.zeros((ch // 4 + 40, cw // 4 + 40), np.uint8); sh[20:-20, 20:-20] = 255; sh = cv2.GaussianBlur(sh, (0, 0), 9)
    q = quad3d(cw * 1.12 + 0, ch * 1.2, cx + 14 * K, cy + 26 * K, 30 * K, R, cam=cam, local_roll=lroll)
    draw_plane(canvas, np.zeros((sh.shape[0], sh.shape[1], 3), np.uint8), sh, q, shadow)
    im = img.copy(); cv2.rectangle(im, (0, 0), (cw - 1, ch - 1), BONE, max(1, int(round(2 * K))))
    draw_plane(canvas, im, np.full((ch, cw), 255, np.uint8), quad3d(cw, ch, cx, cy, 0, R, cam=cam, local_roll=lroll))
    if frame_op > 0.01:
        fk = (key, cw // 8, ch // 8)
        if fk not in A.frame_cache:
            if len(A.frame_cache) > 40: A.frame_cache.clear()
            A.frame_cache[fk] = frame_tex(cw, ch, label, idx)
        pm, a = A.frame_cache[fk]
        s_ = cw / (fk[1] * 8) if False else 1.0
        draw_plane(canvas, pm, a, quad3d(a.shape[1], a.shape[0], cx, cy, -34 * K, R, cam=cam, local_roll=lroll), frame_op * 0.9)


def text_plane(canvas, pm, a, R, cx, cy, dz=-110.0, scale=1.0, op=1.0, cam=1.0, lroll=0.0, sy=1.0):
    h, w = a.shape[:2]
    q = quad3d(w, h * sy, cx, cy, dz * K, R, scale=scale, cam=cam, local_roll=lroll)
    draw_plane(canvas, pm, a, q, op)


def pop_in(t, t0, d=0.14): return out_back((t - t0) / d) if t >= t0 else 0.0


# ====================================================================== A. film reel cold open
def film_text(pic, t):
    pw, ph = A.pw, A.ph
    def ink(mask, cx, cy, t0, op=0.9, color=INK):
        if t < t0: return
        u = clamp((t - t0) / 0.30); m = mask
        if u < 1: m = cv2.GaussianBlur(mask, (0, 0), (1 - u) * 5 * K + 0.1)
        pm, a = layer(m, fill=color); comp_pm(pic, pm, a, op * smooth(u * 1.6), int(cx - a.shape[1] / 2), int(cy - a.shape[0] / 2))
    if t < 2.02:
        x = pw * 0.065
        for w, off in (("All", 0.0), ("I", 0.20), ("wanted", 0.36)):
            m = A.ink[w]; ink(m, x + m.shape[1] / 2, ph * 0.47, OPEN + off); x += m.shape[1] + 20 * K
    elif t < 3.92:
        m = A.ink["was"]; ink(m, pw * 0.615, ph * 0.105, OPEN + 1.95)
        m = A.ink["peace."]; ink(m, pw * 0.775, ph * 0.215, OPEN + 2.17)
        ink(A.kanji_peace, pw * 0.055, ph * 0.26, OPEN + 2.30, op=0.55)
    else:
        x = pw * 0.60
        for w, off in (("Nothing", 0.0), ("more.", 0.30)):
            m = A.ink[w]; ink(m, x + m.shape[1] / 2, ph * 0.60, OPEN + 3.60 + off); x += m.shape[1] + 22 * K


def scene_film(t, n):
    pw, ph, sp = A.pw, A.ph, A.sp
    names = ["A1", "A2", "A3"]; cur = max(i for i, nm in enumerate(names) if SH[nm]["t0"] <= t)
    s = SH[names[cur]]
    pic = render_shot(s, t, size=(pw, ph)); film_text(pic, t)
    line = int(16 * K); off = 0
    dtc = t - s["t0"]
    if cur > 0 and dtc < 0.22:                      # frame roll at the splice
        old = render_shot(SH[names[cur - 1]], s["t0"] - 0.01, size=(pw, ph)); film_text(old, s["t0"] - 0.01)
        roll = 1 - out_expo(dtc / 0.22); stack = np.vstack([pic, np.zeros((line, pw, 3), np.uint8), old])
        off = int(roll * (ph + line)); pic = stack[off:off + ph]
        kb = int(roll * 46 * K) | 1
        if kb > 2: pic = cv2.blur(pic, (1, kb))
    pic = cv2.GaussianBlur(pic, (0, 0), 0.7 * K + 0.2)
    fidx = int(t * 24)
    rng = np.random.default_rng(1000 + fidx)
    pic = pic.copy()
    for _ in range(rng.integers(0, 3)):             # scratches
        x = int(rng.integers(0, pw)); y0 = int(rng.integers(0, ph // 2)); y1 = int(rng.integers(ph // 2, ph))
        c = int(rng.choice([36, 70, 215, 235])); cv2.line(pic, (x, y0), (x + int(rng.integers(-3, 4)), y1), (c, c, c), 1, cv2.LINE_AA)
    for _ in range(rng.integers(3, 9)):             # dust
        x, y = int(rng.integers(0, pw)), int(rng.integers(0, ph)); c = int(rng.choice([20, 40, 230]))
        cv2.circle(pic, (x, y), int(rng.integers(1, int(4 * K) + 2)), (c, c, c), -1, cv2.LINE_AA)
    pic = cv2.multiply(pic, A.film_vig, scale=1 / 255.0)
    shift = off % sp
    canvas = A.film_base[shift:shift + H].copy()
    x0 = (W - pw) // 2; y0 = (H - ph) // 2
    canvas[y0:y0 + ph, x0:x0 + pw] = pic
    dim = cv2.convertScaleAbs(pic, alpha=0.5)       # neighbouring frames above/below
    hsl = y0 - line
    if hsl > 0:
        canvas[0:hsl, x0:x0 + pw] = dim[ph - hsl:ph]; canvas[y0 + ph + line:H, x0:x0 + pw] = dim[0:H - (y0 + ph + line)]
    canvas[hsl:y0, x0:x0 + pw] = 0; canvas[y0 + ph:y0 + ph + line, x0:x0 + pw] = 0
    # gate weave + flicker
    dy = 2.6 * K * noise1(t * 0.9, 3.0) + (5 * K if hrand(fidx, 2) > 0.94 else 0); dx = 1.3 * K * noise1(t * 0.7, 8.0)
    canvas = cv2.warpAffine(canvas, np.float32([[1, 0, dx], [0, 1, dy]]), (W, H), borderMode=cv2.BORDER_REPLICATE)
    gain = 1.0 + 0.07 * (hrand(fidx, 5) - 0.5) * 2 - (0.16 if hrand(fidx, 9) > 0.95 else 0)
    canvas = cv2.convertScaleAbs(canvas, alpha=gain * smooth(t / 0.5), beta=0)
    # film burn into the title
    if t > 5.40:
        u = (t - 5.40) / 0.46
        m = np.clip((A.burn + np.linspace(-0.55, 0.45, W, dtype=np.float32)[None, :] - (1.0 - 1.25 * u)) * 5.0, 0, 1)
        core = np.clip((m - 0.55) * 2.4, 0, 1)
        add = (m[..., None] * np.array([[[18, 96, 235]]], np.float32) + core[..., None] * np.array([[[200, 190, 120]]], np.float32))
        canvas = np.clip(canvas.astype(np.float32) + add, 0, 255).astype(np.uint8)
    return canvas


# ====================================================================== B. title = the official logo build (footage, retimed to the beat)
LOGO_T = (5.86, 6.32, 6.78, 7.27, 8.22)        # DEAD | MOUNT | DEATH | full logo ... hold


def scene_logo(t, n):
    fr = CLIPS.get(SH["B"])
    if A.logo_steps is None:                     # the three hard changes in the source: MOUNT, DEATH, full logo
        d = [float(np.abs(fr[i][::8, ::8].astype(np.int16) - fr[i - 1][::8, ::8]).mean()) for i in range(1, min(len(fr), 40))]
        idx = [i + 1 for i, v in enumerate(d) if v > 60][:3]
        A.logo_steps = [0] + idx if len(idx) == 3 else [0, 9, 18, 24]
    st = A.logo_steps; seg = max(i for i in range(4) if t >= LOGO_T[i]); dt = t - LOGO_T[seg]
    if seg < 3:
        ln = st[seg + 1] - st[seg]; fi = st[seg] + min(ln - 1, int(dt / (LOGO_T[seg + 1] - LOGO_T[seg]) * ln))
    else:
        fi = min(len(fr) - 1, st[3] + int(dt * tl.SRC_FPS))
    z = 1.0 + 0.035 * math.exp(-dt / 0.09) + (0.02 * dt / 0.95 if seg == 3 else 0.0)
    push = getattr(tl, "LOGO_PUSH", None)
    if push and t >= push[0]:                      # V4: the camera dives into the "O" of MOUNT (its black counter becomes the skull's eye socket)
        u = clamp((t - push[0]) / (LOGO_T[4] - push[0])); zz = z * push[3] ** (u ** 2.4)
        img = cv2.resize(fr[fi], (W, H)) if fr[fi].shape[1] != W else fr[fi]
        return zoom_at(img, zz, push[1] * W, push[2] * H, lerp(push[1] * W, W / 2, smooth(u * 1.3)), lerp(push[2] * H, H / 2, smooth(u * 1.3)))
    return warp(fr[fi], z, 0.5, 0.5, 0.0, 0.0, 0.0, W, H)


# ====================================================================== C. verse
def stagger(L, t, t0, step=0.024, rise=0.42, d=0.20):
    ls, (tw, th) = L; out = []
    for i in range(len(ls)):
        u = (t - t0 - i * step) / d
        out.append((0.0, (1 - out_back(u)) * th * rise if u > 0 else th, clamp(u * 3.0)))
    return out


def card_pose(t, s, yaw, pitch, roll, intro=0.20):
    u = clamp((t - s["t0"]) / (s["t1"] - s["t0"])); e = out_expo((t - s["t0"]) / intro)
    y = lerp(yaw[0], yaw[1], out_cubic(u)) * e + 1.2 * slow(t, 1.0); p = lerp(pitch[0], pitch[1], out_cubic(u)) * e + 0.8 * slow(t, 2.0)
    r = lerp(roll[0], roll[1], u) * e
    return Rmat(y, p, r), e, u


def scene_verse(t, n, acc):
    cur = [s for s in tl.SHOTS if s["name"].startswith("C") and s["t0"] <= t < s["t1"]][-1]
    nm = cur["name"]
    beat = sum(0.012 * math.exp(-(t - b) / 0.07) for b in tl.B if 0 <= t - b < 0.3)
    if nm == "C2":                                   # MOUNTAIN
        R, e, u = card_pose(t, cur, (-17, -7), (5, 2), (-2.5, -1.0))
        hi = smooth((t - 9.58) / 0.22)
        cw = int(lerp(W * 1.02, W * 0.56, e)) // 2 * 2; ch = cw * 9 // 16 // 2 * 2
        img = render_shot(cur, t, size=(cw, ch)); cx, cy = W * 0.5, lerp(H * 0.5, H * 0.445, e) - hi * H * 0.03
        canvas = backdrop(img); plus_markers(canvas, R, t, 1.0, 0.36 * e)
        card(canvas, img, R, cx, cy, 1 + beat, "C2", A.card_labels["C2"], A.card_idx["C2"], e)
        pm, a = word_layer(A.L_mount, BONE, stagger(A.L_mount, t, 9.10))
        pm, a = with_shadow(pm, a, 10 * K, 0.6, 6 * K)
        sy = 1 + 0.26 * hi
        text_plane(canvas, pm, a, R, cx, cy + ch / 2 + 12 * K - (sy - 1) * a.shape[0] * 0.25, -120, 1.0, 1.0, 1 + beat, sy=sy)
        if t >= 9.58:
            p = pop_in(t, 9.58); text_plane(canvas, *A.script["high"], R, cx + cw * 0.43, cy - ch / 2 + 26 * K, -150, p, clamp(p * 2), 1 + beat, lroll=-9)
        return canvas
    if nm == "C4":                                   # VALLEY
        R, e, u = card_pose(t, cur, (7, 2), (26, 15), (1.5, 0.5))
        lo = smooth((t - 11.50) / 0.22)
        cw = int(lerp(W * 1.02, W * 0.54, e)) // 2 * 2; ch = cw * 9 // 16 // 2 * 2
        img = render_shot(cur, t, size=(cw, ch)); cx, cy = W * 0.5, lerp(H * 0.5, H * 0.40, e) + lo * H * 0.02
        canvas = backdrop(img); plus_markers(canvas, R, t, 2.0, 0.36 * e)
        ls, (tw, th) = A.L_valley; d = out_back((t - 10.96) / 0.26, 1.2)
        pm, a = word_layer(A.L_valley, BONE, [(0, 0, 1.0)] * len(ls)); pm, a = with_shadow(pm, a, 10 * K, 0.6, 6 * K)
        text_plane(canvas, pm, a, R, cx, cy + ch / 2 + lerp(-th * 0.45, th * 0.30, d) + lo * H * 0.03, 70, 1.0, clamp((t - 10.96) / 0.06), 1 + beat)
        card(canvas, img, R, cx, cy, 1 + beat, "C4", A.card_labels["C4"], A.card_idx["C4"], e)
        if t >= 11.50:
            p = pop_in(t, 11.50); text_plane(canvas, *A.script["low"], R, cx + cw * 0.62, cy + ch / 2 + th * 0.10, -150, p, clamp(p * 2), 1 + beat, lroll=-7)
        return canvas
    if nm in ("C6a", "C6b"):                         # RIVER (wide)
        s0 = SH["C6a"]; t0 = s0["t0"]; t1 = SH["C6b"]["t1"]; uu = clamp((t - t0) / (t1 - t0)); e = out_expo((t - t0) / 0.20)
        wd = smooth((t - 13.26) / 0.30)
        R = Rmat(lerp(15, -11, smooth(uu)) * e + slow(t, 4.0), -3 * e, 1.5 * e)
        asp = lerp(16 / 9, 2.9, wd); cw = int(lerp(W * 1.02, W * lerp(0.56, 0.80, wd), e)) // 2 * 2; ch = int(cw / asp) // 2 * 2
        img = render_shot(cur, t, size=(cw, ch)); cx, cy = W * lerp(0.47, 0.53, uu), lerp(H * 0.5, H * 0.45, e)
        canvas = backdrop(img); plus_markers(canvas, R, t, 3.0, 0.36 * e)
        card(canvas, img, R, cx, cy, 1 + beat, "C6", A.card_labels["C6"], A.card_idx["C6"], e)
        ls, (tw, th) = A.L_river; sp_ = wd * 110 * K
        offs = []
        for i in range(len(ls)):
            ui = (t - 12.59 - i * 0.03) / 0.18
            offs.append(((i - 2) * sp_ + tw * 0.35, (1 - out_back(ui)) * th * 0.4 + math.sin(t * 7.0 + i * 0.9) * 9 * K if ui > 0 else th, clamp(ui * 3)))
        pm, a = word_layer(A.L_river, BONE, offs, wmul=1.7); pm, a = with_shadow(pm, a, 10 * K, 0.6, 6 * K)
        text_plane(canvas, pm, a, R, cx + (uu - 0.5) * W * 0.10, cy + ch / 2 + 16 * K, -120, 1.0, 1.0, 1 + beat)
        if t >= 13.26:
            p = pop_in(t, 13.26); text_plane(canvas, *A.script["wide"], R, cx + cw * 0.44, cy - ch / 2 + 22 * K, -150, p, clamp(p * 2), 1 + beat, lroll=-8)
        return canvas
    # ---- full-frame punches
    if nm == "C1":
        img, m = render_shot(cur, t, acc, want_matte=True); canvas = img.copy()
        if t >= 8.59:
            p = pop_in(t, 8.59, 0.18); pm, a = A.script["aint_big"]
            put(canvas, pm, a, W * 0.265, H * 0.33 - (1 - p) * 30 * K, scale=lerp(0.8, 1.0, p) * (1 + 0.03 * (t - 8.59)), rot=-8, opacity=clamp(p * 2))
            if m is not None: comp_matte(canvas, img, m)
        return canvas
    canvas = full(t, acc)
    if 10.48 <= t < 10.96:
        p = pop_in(t, 10.48); put(canvas, *A.script["aint"], W * 0.20, H * 0.70, scale=p, rot=-7, opacity=clamp(p * 2))
    if 12.10 <= t < 12.59:
        p = pop_in(t, 12.10); put(canvas, *A.script["aint"], W * 0.79, H * 0.30, scale=p, rot=5, opacity=clamp(p * 2))
    if 14.08 <= t < 14.86:
        dt = t - 14.08; e = out_expo(dt / 0.12); j = 5 * K * math.exp(-dt / 0.2)
        put(canvas, *A.enough_v, W * 0.5 + j * noise1(t * 3, 2), H * 0.70 + j * noise1(t * 3, 5), scale=lerp(1.55, 1.0, e) * (1 + 0.03 * dt), rot=-4, opacity=clamp(dt / 0.04))
    if 14.80 <= t < 15.36:
        p = pop_in(t, 14.80); put(canvas, *A.script["baby"], W * 0.77, H * 0.80, scale=p, rot=-9, opacity=clamp(p * 2) * clamp((15.36 - t) / 0.08))
    return canvas


# ====================================================================== D. reincarnation -> Shinjuku
def scene_d(t, n, acc):
    if 19.50 <= t < 21.34:
        return scene_duo(t, n, acc)
    canvas = full(t, acc)
    if 16.15 <= t < 17.28:
        p = clamp((t - 16.15) / 0.2); put(canvas, *A.script["ifyou"], W * 0.27, H * 0.74 - (1 - out_cubic(p)) * 12 * K, rot=-4, opacity=p * clamp((17.28 - t) / 0.12))
    if 17.28 <= t < 17.65:
        dt = t - 17.28; e = out_expo(dt / 0.12)
        put(canvas, *A.callme, W * 0.66, H * 0.72, scale=lerp(1.35, 1.0, e) * (1 + 0.02 * dt), opacity=clamp(dt / 0.04))
    if 17.65 <= t < 19.70:                           # location card
        dt = t - 17.65; fo = clamp((19.70 - t) / 0.18); u = out_cubic(dt / 0.34)
        g = np.clip(1.0 - np.arange(W, dtype=np.float32) / (W * 0.30), 0, 1) ** 1.4 * 0.62 * fo * clamp(dt / 0.25)
        canvas[:] = (canvas.astype(np.float32) * (1 - g)[None, :, None]).astype(np.uint8)
        m = A.shinjuku.copy(); m[int(m.shape[0] * u):] = 0
        pm, a = layer(m, fill=BONE, stroke=((20, 10, 26), 4 * K), shadow=(10 * K, 0.6, 0, 5 * K)); x = int(W * 0.045); y = int(H * 0.5 - A.shinjuku.shape[0] / 2)
        comp_pm(canvas, pm, a, 0.96 * fo, x - (a.shape[1] - A.shinjuku.shape[1]) // 2, y - (a.shape[0] - A.shinjuku.shape[0]) // 2)
        xr = x + A.shinjuku.shape[1] + int(22 * K); yl0, yl1 = int(H * 0.5 - A.shinjuku.shape[0] / 2), int(H * 0.5 + A.shinjuku.shape[0] / 2)
        cv2.line(canvas, (xr, yl0), (xr, int(lerp(yl0, yl1, out_cubic((dt - 0.1) / 0.4)))), tuple(int(c * fo) for c in BONE), max(1, int(2 * K)), cv2.LINE_AA)
        if dt > 0.25:
            pm, a = layer(A.loc_lab, fill=BONE); comp_pm(canvas, pm, a, 0.9 * fo * clamp((dt - 0.25) / 0.2), xr + int(12 * K), yl1 - a.shape[0])
            comp_pm(canvas, *A.loc_co, 0.8 * fo * clamp((dt - 0.4) / 0.2), x, yl1 + int(16 * K))
    if 18.31 <= t < 19.62:
        fo = clamp((19.62 - t) / 0.12); p = pop_in(t, 18.31)
        pm, a = A.script["nomatter"]; put(canvas, pm, a, W * 0.955 - a.shape[1] / 2, H * 0.62, scale=p, rot=-5, opacity=clamp(p * 2) * fo)
        if t >= 18.55:
            dt = t - 18.55; e = out_expo(dt / 0.14); pm, a = A.where
            put(canvas, pm, a, W * 0.955 - a.shape[1] / 2, H * 0.755 + (1 - e) * 26 * K, opacity=clamp(dt / 0.06) * fo)
    return canvas


def scene_duo(t, n, acc=ZERO_ACC):
    u = clamp((t - 19.50) / 1.84); e = out_expo((t - 19.50) / 0.30); far = smooth((t - 19.75) / 1.55)
    R = Rmat(lerp(0, -9, far) + slow(t, 5), 2 * slow(t, 6), 0)
    cw = int(W * 0.44) // 2 * 2; ch = cw * 9 // 16 // 2 * 2
    il = render_shot(SH["D5L"], t, size=(cw, ch)); ir = render_shot(SH["D5R"], t, size=(cw, ch))
    canvas = cv2.addWeighted(backdrop(il, 0.16), 1.0, backdrop(ir, 0.14), 1.0, 0)
    canvas[:] = cv2.convertScaleAbs(canvas, alpha=e)
    if e < 0.995 and t < SH["D4"]["t1"]: canvas[:] = cv2.addWeighted(canvas, 1.0, full(t, acc), 1 - e, 0)     # street shot recedes under the cards
    plus_markers(canvas, R, t, 5.0, 0.36 * e)
    lx, ly, lz = lerp(W * 0.27, W * 0.16, far), lerp(H * 0.5, H * 0.30, far) + (1 - e) * H, lerp(0, 1900 * K, far)
    rx, ry, rz = lerp(W * 0.73, W * 0.70, far), lerp(H * 0.5, H * 0.56, far) - (1 - e) * H, lerp(0, -300 * K, far)
    Rl = Rmat(lerp(0, 30, far), 0, lerp(0, -3, far))
    # connecting dashed line + label
    f = 1.7 * W
    def scr(x, y, z, Rm):
        p = np.array([x - W / 2, y - H / 2, z]) @ Rm.T; return np.array([W / 2 + f * p[0] / (f + p[2]), H / 2 + f * p[1] / (f + p[2])])
    pa, pb = np.array([lx, ly]), scr(rx, ry, rz, R)
    if far > 0.05:
        nseg = 26; col = tuple(int(c * 0.7 * far) for c in BONE)
        for i in range(0, nseg, 2):
            a_, b_ = pa + (pb - pa) * i / nseg, pa + (pb - pa) * (i + 1) / nseg
            cv2.line(canvas, (int(a_[0]), int(a_[1])), (int(b_[0]), int(b_[1])), col, max(1, int(1.5 * K)), cv2.LINE_AA)
    # far card (other world)
    canvas_l = canvas
    ql = quad3d(cw, ch, lx, ly, lz, None, Rl=Rl, screen=True); im = il.copy(); cv2.rectangle(im, (0, 0), (cw - 1, ch - 1), BONE, max(1, int(3 * K)))
    im = cv2.convertScaleAbs(im, alpha=lerp(1.0, 0.72, far))
    draw_plane(canvas_l, im, np.full((ch, cw), 255, np.uint8), ql)
    card(canvas, ir, R, rx, ry, 1.0, "D5R", None, None, e * 0.9)
    # labels
    for (kj, mn), q in ((A.lab_other, ql), (A.lab_shin, quad3d(cw, ch, rx, ry, rz, R))):
        x, y = int(q[3][0]), int(q[3][1] + 12 * K)
        comp_pm(canvas, *kj, 0.9 * e, x, y); comp_pm(canvas, *mn, 0.85 * e, x + kj[1].shape[1] + int(12 * K), y + int(8 * K))
    if far > 0.3:
        mid = (pa + pb) / 2; pm, a = A.apart; ang = -math.degrees(math.atan2(pb[1] - pa[1], pb[0] - pa[0]))
        put(canvas, pm, a, mid[0], mid[1] - 16 * K, rot=-ang, opacity=clamp((far - 0.3) / 0.2) * 0.9)
    if t >= 20.14:
        p = pop_in(t, 20.14); pm, a = A.script["nomatter"]; put(canvas, pm, a, W * 0.29, H * 0.645, scale=p, rot=-6, opacity=clamp(p * 2))
    if t >= 20.42:
        ls, (tw, th) = A.L_howfar; spread = smooth((t - 20.70) / 0.6) * 46 * K
        offs = []
        for i in range(len(ls)):
            ui = (t - (20.42 if i < 3 else 20.70) - (i % 3) * 0.03) / 0.16
            offs.append(((i - 2.5) * spread + tw * 0.2, (1 - out_back(ui)) * th * 0.35 if ui > 0 else th, clamp(ui * 3)))
        pm, a = word_layer(A.L_howfar, BONE, offs, wmul=1.4); pm, a = with_shadow(pm, a, 10 * K, 0.6, 6 * K)
        put(canvas, pm, a, W * 0.46, H * 0.795)
    return canvas


# ====================================================================== E. polaroids
PH = [dict(name="PH1", pos=(0.235, 0.43), rot=-8, sc=1.0, cap=0, al="l"), dict(name="PH2", pos=(0.76, 0.41), rot=6, sc=1.0, cap=1, al="r"),
      dict(name="PH3", pos=(0.55, 0.70), rot=3, sc=0.98, cap=2, al="l"), dict(name="PH4", pos=(0.50, 0.47), rot=-3, sc=1.12, cap=3, al="c")]


def photo_tex(p, t):
    s = SH[p["name"]]; iw, ih, pb, pbb, ptop = A.iw, A.ih, A.pb, A.pbb, A.ptop
    cwid, chei = iw + 2 * pb, ih + pb + pbb
    tex = np.zeros((chei + ptop, cwid, 3), np.uint8); al = np.zeros((chei + ptop, cwid), np.uint8)
    tex[ptop:] = A.paper; al[ptop:] = 255
    if s["matte"]: img, m = render_shot(s, t, size=(iw, ih), want_matte=True, t_clamp=True)
    else: img, m = render_shot(s, t, size=(iw, ih)), None
    tex[ptop + pb:ptop + pb + ih, pb:pb + iw] = img
    cv2.rectangle(tex, (pb, ptop + pb), (pb + iw - 1, ptop + pb + ih - 1), (60, 56, 60), 1)
    if m is not None:                                 # character pops out over the top border
        land = clamp((t - s["t0"] - 0.25) / 0.35); sc = 1.0 + 0.11 * out_cubic(land)
        if sc > 1.005:
            nw, nh = int(iw * sc), int(ih * sc)
            big = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR); bm = cv2.resize(m, (nw, nh), interpolation=cv2.INTER_LINEAR)
            x0 = (nw - iw) // 2; big = big[:, x0:x0 + iw]; bm = bm[:, x0:x0 + iw].copy()
            ytop = ptop + pb + ih - nh
            bm[:, :2] = 0; bm[:, -2:] = 0
            yy0 = max(0, ytop); roi = tex[yy0:ptop + pb + ih, pb:pb + iw]; sm_ = bm[yy0 - ytop:]; sb = big[yy0 - ytop:]
            comp_matte(roi, sb, sm_); al[yy0:ptop + pb, pb:pb + iw] = cv2.max(al[yy0:ptop + pb, pb:pb + iw], sm_[:ptop + pb - yy0])
    # handwriting (write-on)
    cm = A.names[p["cap"]]; u = clamp((t - s["t0"] - 0.22) / 0.38)
    if u > 0:
        c2 = cm.copy(); c2[:, int(c2.shape[1] * u):] = 0
        pm, a = layer(c2, fill=(46, 30, 26)); h, w = a.shape
        Mr = cv2.getRotationMatrix2D((w / 2, h / 2), 3, 1.0)
        pm = cv2.warpAffine(pm, Mr, (w, h)); a = cv2.warpAffine(a, Mr, (w, h))
        cxp = {"l": pb + int(18 * K), "r": pb + iw - w - int(18 * K), "c": pb + (iw - w) // 2}[p["al"]]
        comp_pm(tex, pm, a, 0.95, cxp, ptop + pb + ih + (pbb - h) // 2)
    return premult(tex, al), al


def scene_polaroid(t, n):
    canvas = A.table.copy()
    zt = smooth((t - 25.54) / 0.26)                   # zoom-through into the last photo
    drift = (t - 22.04) / 3.5
    p4 = PH[3]; icx_off = 0.0; icy_off = -(A.pbb - A.pb) / 2 * p4["sc"]      # image centre relative to card centre
    for i, p in enumerate(PH):
        s = SH[p["name"]]
        if t < s["t0"]: continue
        dt = t - s["t0"]; e = out_expo(dt / 0.22); sgn = 1 if i % 2 == 0 else -1
        pm, a = photo_tex(p, t)
        sc = p["sc"] * lerp(1.55, 1.0, e) * (1 + 0.04 * drift); rot = p["rot"] + sgn * 13 * (1 - e) + 0.8 * slow(t, i + 1.0)
        cx = W * p["pos"][0] + (W * 0.5 - W * p["pos"][0]) * -0.04 * drift; cy = H * p["pos"][1] - (1 - e) * H * 0.10
        cy += -A.ptop / 2 * sc                        # texture has extra head-room on top
        if zt > 0:                                    # camera flies into photo 4's picture
            tx, ty = W * p4["pos"][0], H * p4["pos"][1] + icy_off
            zs = lerp(1.0, (W / (A.iw * p4["sc"])) * 1.02, in_expo(zt) * 0.5 + zt * 0.5)
            cx = W / 2 + (cx - tx) * zs + (tx - W / 2) * (1 - zt); cy = H / 2 + (cy - ty) * zs + (ty - H / 2) * (1 - zt)
            sc *= zs; rot = lerp(rot, rot - p4["rot"], zt)
        op = clamp(dt / 0.05)
        shs = A.pshadow; so = lerp(26, 14, e) * K
        put(canvas, np.zeros((shs.shape[0], shs.shape[1], 3), np.uint8), shs, cx + so * 0.6, cy + A.ptop / 2 * sc + so, scale=sc, rot=rot, opacity=0.55 * op)
        put(canvas, pm, a, cx, cy, scale=sc, rot=rot, opacity=op)
    fo = 1 - zt
    if t < 23.50:
        p = pop_in(t, 22.04, 0.2); pm, a = A.script["dontworry"]
        put(canvas, pm, a, W * 0.045 + a.shape[1] / 2, H * 0.115, scale=p, rot=-3, opacity=clamp(p * 2) * clamp((23.50 - t) / 0.15))
    if t >= 23.54:
        p = pop_in(t, 23.54, 0.2); pm, a = A.script["justcall"]
        put(canvas, pm, a, W * 0.04 + a.shape[1] / 2, H * 0.895, scale=p, rot=-3, opacity=clamp(p * 2) * fo)
    return canvas


# ====================================================================== E action + pocket
def scene_action(t, n, acc):
    canvas = full(t, acc)
    if t < 26.47:
        x = W * 0.20
        for (pm, a), t0 in zip(A.illbe, (25.80, 25.84, 25.97)):
            if t >= t0:
                e = out_expo((t - t0) / 0.12); put(canvas, pm, a, x + a.shape[1] / 2 + (1 - e) * 60 * K, H * 0.76, opacity=clamp((t - t0) / 0.05) * clamp((26.47 - t) / 0.06))
            x += a.shape[1] - 14 * K
    if 26.45 <= t < 27.38:
        dt = t - 26.45; e = out_expo(dt / 0.16); pm, a = A.hurry
        xoff = (1 - e) * W * 0.7 - dt * 40 * K
        if e < 0.97:
            kb = int((1 - e) * 120 * K) | 1; pm = cv2.blur(pm, (kb, 1)); a = cv2.blur(a, (kb, 1))
        put(canvas, pm, a, W * 0.5 + xoff, H * 0.74, rot=-3, opacity=clamp(dt / 0.04) * clamp((27.38 - t) / 0.06))
    if 27.50 <= t < 28.55:
        fo = clamp((28.55 - t) / 0.06); p = pop_in(t, 27.50); pm, a = A.script["youdont"]
        put(canvas, pm, a, W * 0.70, H * 0.60, scale=p, rot=-5, opacity=clamp(p * 2) * fo)
        if t >= 28.07:
            dt = t - 28.07; e = out_expo(dt / 0.12); pm, a = A.worry; cx, cy = W * 0.70, H * 0.765
            put(canvas, pm, a, cx, cy, scale=lerp(1.25, 1.0, e), opacity=clamp(dt / 0.04) * fo)
            if t >= 28.30:                           # marker strike-through
                u = out_cubic((t - 28.30) / 0.16); x0, x1 = cx - a.shape[1] * 0.50, cx + a.shape[1] * 0.50
                pts = [(int(lerp(x0, x1, v)), int(cy + 6 * K + math.sin(v * 9) * 5 * K - v * 14 * K)) for v in np.linspace(0, u, 24)]
                for pa, pb in zip(pts, pts[1:]): cv2.line(canvas, pa, pb, RED, max(2, int(13 * K)), cv2.LINE_AA)
    return canvas


def scene_pocket(t, n):
    s1, s2 = SH["P1"], SH["P2"]; cur = s1 if t < s2["t0"] else s2
    g0 = tl.CHORUS - 0.55; grow = in_expo((t - g0) / 0.55) if t > g0 else 0.0
    R = Rmat(lerp(9, -5, smooth((t - 28.55) / 1.95)) * (1 - grow), (3 + 1.5 * slow(t, 3)) * (1 - grow), -1.5 * (1 - grow))
    hb = sum(0.022 * math.exp(-(t - b) / 0.10) for b in (28.70, 28.98, 29.60, 29.88) if t >= b)
    cw = int(lerp(W * 0.50, W * 1.03, grow)) // 2 * 2; ch = cw * 9 // 16 // 2 * 2
    e = out_expo((t - 28.55) / 0.22)
    cx, cy = W * 0.5, lerp(H * 0.44, H * 0.5, grow)
    if cur is s1: img, m = render_shot(cur, t, size=(cw, ch), want_matte=True)
    else: img, m = render_shot(cur, t, size=(cw, ch)), None
    canvas = backdrop(img, 0.13 * (1 - grow)); plus_markers(canvas, R, t, 7.0, 0.3 * (1 - grow))
    card(canvas, img, R, cx, cy, (1 + hb) * lerp(1.12, 1.0, e), "P", A.card_labels["P"], A.card_idx["P"], (1 - grow) * e)
    if m is not None:                                 # the three of them lean out over the top border
        sc = 1.07; nw, nh = int(cw * sc), int(ch * sc)
        big = cv2.resize(img, (nw, nh)); bm = cv2.resize(m, (nw, nh)); x0 = (nw - cw) // 2
        big = big[:, x0:x0 + cw]; bm = bm[:, x0:x0 + cw].copy(); bm[:, :3] = 0; bm[:, -3:] = 0
        draw_plane(canvas, premult(big, bm), bm, quad3d(cw, nh, cx, cy - (nh - ch) / 2, -60 * K, R, cam=(1 + hb) * lerp(1.12, 1.0, e)))
    # dialogue
    fo = 1.0
    words = list(zip(A.d_prot, (0.0, 0.50, 0.78)))
    tot = sum(a.shape[1] for (pm, a), _ in words) - 2 * 30 * K; x = W * 0.5 - tot / 2; yb = lerp(cy + ch / 2 + 6 * K, H * 0.70, grow)
    for (pm, a), off in words:
        if t >= MID + off:
            u = clamp((t - MID - off) / 0.16); put(canvas, pm, a, x + a.shape[1] / 2, yb + (1 - out_cubic(u)) * 10 * K, opacity=u)
        x += a.shape[1] - 30 * K
    words = list(zip(A.d_nmw, (1.06, 1.18, 1.44)))
    tot = sum(a.shape[1] for (pm, a), _ in words) - 2 * 26 * K; x = W * 0.5 - tot / 2
    for (pm, a), off in words:
        if t >= MID + off:
            u = (t - MID - off); e2 = out_expo(u / 0.12); put(canvas, pm, a, x + a.shape[1] / 2, yb + 132 * K, scale=lerp(1.3, 1.0, e2), opacity=clamp(u / 0.04))
        x += a.shape[1] - 26 * K
    return canvas


# ====================================================================== F. chorus
def slam(canvas, pm, a, R, cx, cy, t, t0, dz=-60, lroll=0.0, sy=1.0, grow=0.05, sc=1.0):
    dt = t - t0
    if dt < 0: return
    e = out_expo(dt / 0.11)
    for g, op in ((0.30, 0.18), (0.15, 0.32)):        # trailing ghosts
        if e < 0.98: text_plane(canvas, pm, a, R, cx, cy, dz, sc * lerp(1.7, 1.0, clamp(e - g * (1 - e))), op * (1 - e), lroll=lroll, sy=sy)
    text_plane(canvas, pm, a, R, cx, cy, dz, sc * lerp(1.7, 1.0, e) * (1 + grow * dt), clamp(dt / 0.03), lroll=lroll, sy=sy)


def scene_chorus(t, n, acc):
    if t >= SH["F6"]["t0"]:                           # the last word sits BEHIND Polka (cut-out)
        s = SH["F6"]; dt = t - s["t0"]
        canvas = render_shot(s, t, acc).copy()
        fg, m = render_shot(s, t, acc, want_matte=True, zmul=1.045)
        e = out_expo(dt / 0.12); j = 6 * K * math.exp(-dt / 0.25); sc_ = lerp(1.5, 1.0, e) * 0.86 * (1 + 0.035 * dt)
        for (pm, a), sg in ((A.c_en_l, -1), (A.c_en_r, 1)):       # the word splits around his head, tucked behind him
            cx = W * 0.5 + sg * W * (0.292 + 0.10 * (1 - e)); cy = H * 0.345 - sg * W * 0.292 * 0.052
            put(canvas, pm, a, cx + j * noise1(t * 3, 1), cy + j * noise1(t * 3, 4), scale=sc_, rot=-3, opacity=clamp(dt / 0.03) * clamp((33.60 - t) / 0.22))
        if m is not None: comp_matte(canvas, fg, m)
        return canvas
    canvas = full(t, acc)
    if t < 30.96:
        slam(canvas, *A.c_aint, Rmat(26, -5, 0), W * 0.37, H * 0.52, t, tl.CHORUS, lroll=-4)
    elif t < 31.44:
        dt = t - 30.96; sp = out_expo(dt / 0.16) * W * 0.20 + dt * 60 * K; R = Rmat(0, 16, 0)
        for (pm, a), sg in zip(A.c_no, (-1, 1)):
            slam(canvas, pm, a, R, W * 0.5 + sg * (a.shape[1] * 0.40 + sp), H * 0.5, t, 30.96, lroll=sg * 3.0)
    elif t < 31.89:
        dt = t - 31.44; R = Rmat(0, -44, 0); pm, a = A.c_mount
        slam(canvas, pm, a, R, W * 0.5, H * 0.60 - dt * 90 * K, t, 31.44, dz=0, sy=1.9)
    elif t < 32.44:
        dt = t - 31.89; pm, a = A.c_high
        slam(canvas, pm, a, Rmat(24, 0, 0), W * 0.205, H * 0.56 - out_cubic(dt / 0.5) * H * 0.07, t, 31.89, lroll=-4, sy=1 + 0.9 * out_cubic(dt / 0.45), sc=0.46)   # beside the true form, stretching tall
    return canvas


# ====================================================================== G. outro + end title
FINALE_HOOK = None
END_MAP = [(35.85, 1300.90), (36.85, 1300.00), (36.85, 1299.80), (37.45, 1297.52), (37.45, 1297.45), (37.55, 1297.27), (37.55, 1297.14), (39.30, 1296.00)]


def end_logo_frame(t):
    """the official title card, played backwards: Shinjuku skyline -> logo glitches in -> static -> logo on white."""
    s = SH["G2"]; fr = CLIPS.get(s); src = END_MAP[0][1] if t < END_MAP[0][0] else END_MAP[-1][1]
    for (ta, sa), (tb, sb) in zip(END_MAP, END_MAP[1:]):
        if ta <= t < tb: src = lerp(sa, sb, (t - ta) / (tb - ta)); break
    fi = max(0, min(len(fr) - 1, int(round((src - s["ss"]) * tl.SRC_FPS))))
    z = 1.0 + 0.03 * (1 - smooth((t - 35.85) / 1.0))
    return warp(fr[fi], z, 0.5, 0.5, 0.0, 0.0, 0.0, W, H)


def scene_outro(t, n, acc):
    canvas = np.zeros((H, W, 3), np.uint8); g1 = None
    if t < SH["F6"]["t1"]: canvas = FINALE_HOOK(t, acc) if FINALE_HOOK else render_shot(SH["F6"], t, acc)
    if SH["G1"]["t0"] <= t < SH["G1"]["t1"]:
        img, g1m = render_shot(SH["G1"], t, acc, want_matte=True); g1 = (img, g1m)
        a = clamp((t - SH["G1"]["t0"]) / SH["G1"]["fin"])
        canvas = img.copy() if a >= 0.999 else cv2.addWeighted(canvas, 1 - a, img, a, 0)
    if t >= SH["G2"]["t0"]:
        img = end_logo_frame(t); a = clamp((t - SH["G2"]["t0"]) / 0.4)
        canvas = img.copy() if a >= 0.999 else cv2.addWeighted(canvas, 1 - a, img, a, 0)
    fo = clamp((36.85 - t) / 0.30)
    if t >= 35.57 and fo > 0:                         # "peaceful." tucked behind him
        dt = t - 35.57; e = out_expo(dt / 0.22); pm, a = A.peaceful
        put(canvas, pm, a, W * 0.685, H * 0.60 + (1 - e) * 30 * K, scale=lerp(0.9, 1.0, e) * (1 + 0.02 * dt), rot=-4, opacity=clamp(dt / 0.12) * fo)
        if g1 is not None and g1[1] is not None and t < SH["G1"]["t1"]:
            k = clamp((SH["G1"]["t1"] - t) / 0.4)
            comp_matte(canvas, g1[0], cv2.convertScaleAbs(g1[1], alpha=k) if k < 1 else g1[1])
    if t >= 36.05 and fo > 0:
        pm, a = A.kanji_peace_w; comp_pm(canvas, pm, a, 0.9 * clamp((t - 36.05) / 0.3) * fo, int(W * 0.06), int(H * 0.5 - a.shape[0] / 2))
    if CLOSE <= t < 36.15:                             # the line itself, lower-left
        offs = ((0.0, 0.12, 0.40, 0.64), (0.90, 1.12, 1.36, 1.58)); f2 = clamp((36.15 - t) / 0.3)
        for li, (ln, of) in enumerate(zip(A.d_close, offs)):
            x = W * 0.055
            for (pm, a), off in zip(ln, of):
                if t >= CLOSE + off:
                    u = clamp((t - CLOSE - off) / 0.16); put(canvas, pm, a, x + a.shape[1] / 2, H * (0.665 + 0.082 * li) + (1 - out_cubic(u)) * 8 * K, opacity=u * f2)
                x += a.shape[1] - 26 * K
    return canvas


# ====================================================================== post + dispatch
def post(img, t, acc, n, grain=0.085, glow0=0.10, vig=1.0, ca=True, streak=True):
    ga = glow0 + acc["glow"]
    sm = cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    br = cv2.subtract(sm, np.full_like(sm, 140))
    bl = cv2.GaussianBlur(br, (0, 0), W / 4 * 0.022)
    img = cv2.addWeighted(img, 1.0, cv2.resize(bl, (W, H), interpolation=cv2.INTER_LINEAR), ga * 2.2, 0)
    if streak and (8.22 <= t < 15.5 or 25.8 <= t < 33.6):           # anamorphic streak on the magic
        st = cv2.blur(cv2.subtract(sm, np.full_like(sm, 185)), (int(W / 4 * 0.42) | 1, 1))
        st = cv2.multiply(st, np.full_like(st, (255, 170, 120)), scale=1 / 255.0)
        img = cv2.addWeighted(img, 1.0, cv2.resize(st, (W, H), interpolation=cv2.INTER_LINEAR), 1.5, 0)
    e = (0.7 + acc["rgb"]) * 0.0011
    if e > 0.0004 and t >= 5.86 and ca:
        b, g, r = cv2.split(img)
        r = cv2.warpAffine(r, np.float32([[1 + e, 0, -e * W / 2], [0, 1 + e, -e * H / 2]]), (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
        b = cv2.warpAffine(b, np.float32([[1 - e, 0, e * W / 2], [0, 1 - e, e * H / 2]]), (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
        img = cv2.merge([b, g, r])
    fl = acc["flash"]
    if 15.40 <= t < 16.45: fl += smooth((t - 15.40) / 0.37) if t < 15.77 else 1 - smooth((t - 15.77) / 0.68)
    if 16.67 <= t < 17.0: fl += 0.35 * (1 - (t - 16.67) / 0.33)
    if 5.86 <= t < 6.06: fl += 0.75 * (1 - (t - 5.86) / 0.20)
    if tl.CHORUS <= t < tl.CHORUS + 0.3: fl += 0.55 * (1 - (t - tl.CHORUS) / 0.3)
    if hasattr(tl, "FLASHES"):
        for f0, fd, fa in tl.FLASHES:
            if f0 <= t < f0 + fd: fl += fa * (1 - (t - f0) / fd)
    else:
        if 25.80 <= t < 25.98: fl += 0.6 * (1 - (t - 25.80) / 0.18)
        for ph in PH:
            d = t - SH[ph["name"]]["t0"]
            if 22.0 < t < 25.6 and 0 <= d < 0.10: fl += 0.22 * (1 - d / 0.10)       # camera flash as each photo lands
    if fl > 0.004: img = cv2.addWeighted(img, 1.0, np.full_like(img, 255), min(fl, 1.0), 0)
    img = cv2.addWeighted(img, 1.0, A.noise[(n // max(1, FPS // 24)) % 6], grain, -128 * grain)
    if vig <= 0.001: return img
    return cv2.multiply(img, A.vig if vig >= 0.999 else cv2.addWeighted(A.vig, vig, np.full_like(A.vig, 255), 1 - vig, 0), scale=1 / 255.0)


def frame_at(n):
    t = n / FPS; acc = accents(t); grain = 0.085; glow0 = 0.10; vig = 1.0; ca = True
    if t < 5.86: canvas = scene_film(t, n); acc = ZERO_ACC; grain = 0.19
    elif t < 8.22: canvas = scene_logo(t, n); acc = ZERO_ACC; glow0 = 0.0; vig = 0.0; ca = False; grain = 0.05      # the logo stays clean
    elif t < 15.77: canvas = scene_verse(t, n, acc)
    elif t < 21.34: canvas = scene_d(t, n, acc)
    elif t < 22.04: canvas = full(t, acc)
    elif t < 25.80: canvas = scene_polaroid(t, n)
    elif t < 28.55: canvas = scene_action(t, n, acc)
    elif t < tl.CHORUS: canvas = scene_pocket(t, n)
    elif t < 33.60: canvas = scene_chorus(t, n, acc)
    else:
        canvas = scene_outro(t, n, acc)
        if t >= 36.85: vig = clamp((37.45 - t) / 0.6); glow0 = 0.10 * vig; ca = t < 37.45; grain = 0.085 if t < 37.45 else 0.05
    canvas = post(canvas, t, acc, n, grain, glow0, vig, ca)
    bar = int(round(tl.letterbox(t) * H))
    if bar > 0: canvas[:bar] = 0; canvas[H - bar:] = 0
    if t > tl.END - 0.30: canvas = cv2.convertScaleAbs(canvas, alpha=clamp((tl.END - t) / 0.30))
    return canvas


def worker(args):
    global A
    wi, n0, n1 = args
    cv2.setNumThreads(1); A = Assets()
    out = f"{ROOT}/out/{MODE}2_part{wi}.mp4"
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
    n0, n1 = int(round(T0 * FPS)), int(round(T1 * FPS)); NW = 4; step = math.ceil((n1 - n0) / NW)
    jobs = [(i, n0 + i * step, min(n1, n0 + (i + 1) * step)) for i in range(NW) if n0 + i * step < n1]
    with mp.Pool(len(jobs)) as pool: parts = pool.map(worker, jobs)
    with open(f"{ROOT}/out/{MODE}2_parts.txt", "w") as f:
        for p in parts: f.write(f"file '{p}'\n")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{ROOT}/out/{MODE}2_parts.txt", "-c", "copy", f"{ROOT}/out/{MODE}2_video.mp4"], check=True)
    print("wrote", f"{ROOT}/out/{MODE}2_video.mp4", n1 - n0, "frames")
