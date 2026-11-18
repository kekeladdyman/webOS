"""V8 renderer (feedback 6): nothing is a raw clip any more. Manga pages that build themselves, cut-out puppets on designed
backgrounds, split VS panels, sliced frames, type behind characters, dot dissolves. usage: render8.py [draft|final] [t0 t1]"""
import os, sys, json, math
os.environ["TLMOD"] = "tl8"
import subprocess, multiprocessing as mp
from collections import OrderedDict
from r2core import *
import render7 as R7
import render2 as R2
import render4 as R4
import render6 as R6
import fxcomp as X
import fxtype as FT

SH = tl.BY
YEL = (40, 240, 220)                     # MARATHON chartreuse (BGR)
WHITE = (248, 248, 248); INKC = (14, 12, 14); PAPER = (236, 238, 240)
RED_T = (40, 30, 215); VIO_T = (170, 50, 140); BLUE_T = (200, 110, 30); TEAL_T = (150, 150, 30)
A8 = {}
BEAT8 = 60.0 / 123.05
DW = R7.DW
def P(x, y=None): return x * K if y is None else (x * K, y * K)
def PTS(pts): return [(x * K, y * K) for x, y in pts]


# ======================================================================== sources: frames, looks, mattes (cached)
_LC = OrderedDict(); _MC = OrderedDict()
def _lru(d, k, fn, cap):
    if k in d: d.move_to_end(k); return d[k]
    v = fn(); d[k] = v
    while len(d) > cap: d.popitem(last=False)
    return v


LOOKS = {
    "raw": lambda im: im,
    "manga": lambda im: X.manga(im),
    "manga_g": lambda im: X.manga(im, keep_glow=1.0, solid=0.30),
    "manga_r": lambda im: X.manga(im, tone_col=RED_T),
    "manga_rg": lambda im: X.manga(im, tone_col=RED_T, keep_glow=1.0),
    "manga_v": lambda im: X.manga(im, tone_col=VIO_T, keep_glow=1.0),
    "manga_b": lambda im: X.manga(im, tone_col=BLUE_T, keep_glow=1.0),
    "manga_dark": lambda im: X.manga(im, solid=0.42, tone_hi=0.80),
    "duo_red": lambda im: X.duotone(im, (10, 6, 14), (226, 232, 244), mid=(36, 26, 190)),
    "duo_blue": lambda im: X.duotone(im, (22, 8, 6), (255, 246, 232), mid=(190, 96, 24)),
    "duo_vio": lambda im: X.duotone(im, (16, 6, 14), (245, 225, 255), mid=(160, 36, 120)),
    "duo_gold": lambda im: X.duotone(im, (8, 6, 10), (220, 248, 255), mid=(20, 130, 210)),
    "duo_bone": lambda im: X.duotone(im, (12, 10, 14), (215, 228, 236), mid=(70, 76, 92), gamma=1.15),
}


def fidx(s, t):
    frs = CLIPS.get(s); d = s["t1"] - s["t0"]; dt = clamp(t - s["t0"], 0.0, d)
    st_ = src_time(s, d - dt) if s.get("rev") else src_time(s, dt)
    return max(0, min(len(frs) - 1, int(st_ * tl.SRC_FPS + 1e-4)))


def camof(s, t):
    u = clamp((t - s["t0"]) / max(1e-6, s["t1"] - s["t0"])); ue = out_cubic(u) * 0.6 + u * 0.4
    (x0, y0), (x1, y1) = s["pan"]
    return lerp(s["z"][0], s["z"][1], ue), lerp(x0, x1, ue), lerp(y0, y1, ue), lerp(s["rot"][0], s["rot"][1], ue)


def warpc(img, zoom, cx, cy, rot, dx=0.0, dy=0.0, border=cv2.BORDER_REFLECT_101):
    sh, sw = img.shape[:2]; s = zoom * max(W / sw, H / sh); lim = 0.5 * (1 - 1 / max(zoom, 1.0001))
    cx = clamp(cx, 0.5 - lim, 0.5 + lim); cy = clamp(cy, 0.5 - lim, 0.5 + lim)
    M = cv2.getRotationMatrix2D((cx * sw, cy * sh), rot, s); M[0, 2] += W / 2 - cx * sw + dx; M[1, 2] += H / 2 - cy * sh + dy
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=border, borderValue=0)


def base(name, t, look="raw"):
    s = SH[name]; fi = fidx(s, t)
    def mk():
        im = apply_grade(CLIPS.get(s)[fi], s["grade"])
        return LOOKS[look](im)
    return _lru(_LC, (name, fi, look), mk, 40)


def basem(name, t):
    s = SH[name]; fi = fidx(s, t); ms = CLIPS.matte(s)
    if ms is None: return None
    return _lru(_MC, (name, fi), lambda: X.clean_matte(ms[min(fi, len(ms) - 1)], K), 24)


def src(name, t, look="raw", zm=1.0, dx=0.0, dy=0.0, rot=0.0):
    z, cx, cy, r = camof(SH[name], t); return warpc(base(name, t, look), z * zm, cx, cy, r + rot, dx, dy)


def srcm(name, t, look="raw", zm=1.0, dx=0.0, dy=0.0, rot=0.0):
    z, cx, cy, r = camof(SH[name], t); m = basem(name, t)
    img = warpc(base(name, t, look), z * zm, cx, cy, r + rot, dx, dy)
    if m is None: return img, np.zeros((H, W), np.uint8)
    return img, warpc(m, z * zm, cx, cy, r + rot, dx, dy, border=cv2.BORDER_CONSTANT)


def fit_into(img, pts, zoom=1.0, fx=0.5, fy=0.5, border=cv2.BORDER_REFLECT_101):
    """scale a full frame so it covers the bounding box of a panel polygon, source point (fx,fy) at the box centre."""
    pts = np.asarray(pts, np.float64); x0, y0 = pts.min(0); x1, y1 = pts.max(0)
    s = max((x1 - x0) / W, (y1 - y0) / H) * zoom
    M = np.float32([[s, 0, (x0 + x1) / 2 - s * fx * W], [0, s, (y0 + y1) / 2 - s * fy * H]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_AREA if s < 0.8 else cv2.INTER_LINEAR, borderMode=border, borderValue=0)


def comp_full(canvas, img, m, op=1.0):
    if m is None: return
    if op < 0.999: m = cv2.convertScaleAbs(m, alpha=op)
    a3 = cv2.merge([m] * 3); fg = cv2.multiply(img, a3, scale=1 / 255.0)
    cv2.multiply(canvas, 255 - a3, dst=canvas, scale=1 / 255.0); cv2.add(canvas, fg, dst=canvas)


def stick_full(canvas, img, m, px=8, col=WHITE, px2=0, col2=INKC, shadow=None, s=1.0, rot=0.0, dx=0.0, dy=0.0, ax=None, ay=None, op=1.0, echoes=()):
    """a full-frame cut-out as a sticker: outline(s) + drop shadow, optional tinted echo copies, then the figure."""
    L = X.to_layer(img, m)
    if L is None: return None
    pm, a = X.sticker(L["pm"], L["a"], px * K, col, shadow=(shadow[0] * K, shadow[1] * K, shadow[2] * K, shadow[3]) if shadow else None, px2=px2 * K, col2=col2)
    ax = L["cx"] if ax is None else ax; ay = L["cy"] if ay is None else ay
    c, sn = math.cos(math.radians(rot)), math.sin(math.radians(rot)); ox, oy = L["cx"] - ax, L["cy"] - ay
    cx = ax + (ox * c - oy * sn) * s + dx; cy = ay + (ox * sn + oy * c) * s + dy
    for (ex, ey, ecol, eop, es) in echoes:
        tp, ta = X.tint_layer(pm, a, ecol); X.place(canvas, tp, ta, cx + ex * K, cy + ey * K, s * es, rot, op * eop)
    X.place(canvas, pm, a, cx, cy, s, rot, op)
    return (cx, cy)


# ======================================================================== assets
def zod(word, size, col=YEL, light=None):
    f = "Zodiak-Light.otf" if (light if light is not None else size < 125) else "Zodiak-Thin.otf"
    return FT.flat(FT.glyphs(word, f, size * K, tracking=1 * K), col, shadow=(9 * K, 0.85, 3 * K))


def setup8():
    R7.setup(); k = K; g = lambda txt, f, sz, tr=0.0, var=None: FT.glyphs(txt, f, sz * k, tracking=tr * k, var=var)
    tealw = lambda w, sz=300: FT.metal3d(g(w, "texgyreheroscn-bold.otf", sz, -4), top=(235, 255, 205), bot=(160, 190, 95), depth=0.16, angle=28,
                                         ext=(80, 95, 25), ext_far=(22, 30, 8), glow=((200, 235, 40), 30 * k, 0.65), spec=0.22)
    A8["face"] = FT.metal3d(g("FACE", "texgyreheroscn-bolditalic.otf", 380, -4), top=(245, 248, 250), bot=(110, 112, 118), depth=0.06, angle=40,
                            ext=(60, 60, 66), ext_far=(18, 18, 20), spec=0.75, noise=6, glow=((255, 255, 255), 30 * k, 0.18))
    A8["unmasked"] = tealw("UNMASKED"); A8["demons"] = tealw("DEMONS", 340)
    vr = lambda w, c, sz=230: FT.vrens(g(w, "BarlowCondBlackItalic.ttf", sz, 2), fill=c)
    A8["what"] = [vr("WHAT?", WHITE, 210), vr("WHAT?", (40, 30, 235), 210)]
    A8["f2f"] = [vr("FACE", WHITE, 200), vr("TO", (40, 30, 235), 200), vr("FACE", WHITE, 200)]
    A8["vs"] = vr("VS", WHITE, 260)
    cab = lambda w, sz, top=(250, 250, 250), bot=(196, 196, 204): FT.metal3d(g(w, "CabinetGrotesk-Black.otf", sz, -8), top=top, bot=bot, depth=0.05,
                                                                          ext=(120, 120, 130), ext_far=(60, 60, 70), spec=0.2, shadow=0.4)
    A8["armageddon"] = cab("ARMAGEDDON", 420); A8["mask"] = cab("MASK", 640, (236, 236, 240), (150, 150, 160))
    A8["necro"] = FT.flat(g("NECROMANCER", "LibreBodoniItalic.ttf", 230, 6, var=[700]), (40, 30, 235), glow=((60, 40, 255), 20 * k, 0.25))
    A8["synth"] = FT.flat(g("SYNTHETIC", "BigShouldersStencil.ttf", 360, 4, var=[850]), YEL, shadow=(10 * k, 0.6, 4 * k))
    A8["synth_mono"] = FT.flat(g("SHIGAMI  ×  DMDP   //   16.13   //   “WHO IS WEARING HIS FACE”", "SpaceMono.ttf", 26, 3), YEL)
    A8["t_name"] = FT.flat(g("POLKA SHINOYAMA", "texgyreheros-bold.otf", 150, -2), (245, 245, 245), glow=((255, 230, 220), 18 * k, 0.35), shadow=(12 * k, 0.8, 6 * k))
    A8["t_sub"] = FT.flat(g("THE CORPSE GOD", "texgyreheroscn-bold.otf", 74, 14), (240, 240, 240), shadow=(8 * k, 0.7, 3 * k))
    fine = FT.stack([g(x_, "texgyreheroscn-bold.otf", 30) for x_ in ("AN EDIT BY SHIGAMI.  CUT TO “SYNTHETIC”.  FOOTAGE FROM DEAD MOUNT DEATH PLAY,",
                     "EPISODES 01 02 04 05.  BASED ON THE MANGA BY RYOHGO NARITA AND SHINTA FUJIMOTO.", "NO ONE IS WHO THEY SAY THEY ARE.")], gap=0.40, align="center")
    A8["t_fine"] = FT.flat(fine, (212, 212, 212))
    jp = lambda ch, sz, col=WHITE: layer(FT.glyphs(ch, "YujiSyuku.ttf", sz * k), fill=col, stroke=(INKC, 9 * k), shadow=(8 * k, 0.6, 4 * k, 6 * k))
    A8["go"] = jp("ゴ", 230); A8["don"] = [jp("ド", 300), jp("ン", 300)]
    A8["zz"] = {}
    # dialogue / lyric words (MARATHON serif = Zodiak)
    for w_ in ["CAN", "YOU", "SAY", "YOUR", "OWN", "NAME?", "THE", "BODY", "THAT", "I’M", "IN", "RIGHT", "NOW,", "ITS", "NAME", "IS",
               "I", "DON’T", "EVEN", "FEEL", "LIKE", "I’VE", "GOT"]:
        A8["zz"][w_] = zod(w_, 78)
    A8["polka"] = zod("POLKA", 132, light=True); A8["shino"] = zod("SHINOYAMA.", 132, light=True)
    A8["recog"] = zod("RECOGNIZE", 150, light=False); A8["myself"] = zod("MYSELF", 150, light=False)
    A8["disap"] = zod("DISAPPEARED,", 120, light=True); A8["nothing"] = zod("NOTHING", 110, light=True)
    A8["tears"] = [zod(c, 190, light=False) for c in "TEARS"]
    # restyle the reused scenes: tag captions, mirror words, signature, billing
    R7.X7["tag"] = [[zod(w, 78) for w in ln] for ln in (("WHOEVER", "YOU", "ARE,"), ("IT", "SEEMS", "YOU’RE", "NOT"), ("POLKA", "SHINOYAMA,"),
                                                         ("AT", "LEAST", "NOT"), ("ON", "THE", "INSIDE."))]
    mm = FT.glyphs("MIRROR", "Zodiak-Light.otf", 150 * k)
    R7.X7["mir_l"] = FT.flat(mm, YEL, shadow=(9 * k, 0.8, 3 * k)); R7.X7["mir_r"] = FT.flat(cv2.flip(mm, 1), (200, 210, 230), shadow=(9 * k, 0.6, 3 * k))
    R7.X7["sig"] = FT.vrens(g("SHIGAMI", "BarlowCondBlackItalic.ttf", 58, 2), fill=(236, 236, 236), depth=0.10)
    R7.X7["b1"] = FT.flat(g("AN EDIT BY   SHIGAMI", "texgyreheroscn-bold.otf", 40, 12), (32, 28, 30))
    A8["cardlab"] = FT.flat(g("EP.01  ·  16:43  ·  THE DEAD", "SpaceMono.ttf", 17, 3), YEL)
    A8["cardidx"] = FT.flat(g("N° 07  //  WHAT THEY LEFT", "SpaceMono.ttf", 17, 3), YEL)
    metal = lambda w, sz: FT.metal3d(g(w, "texgyreheroscn-bolditalic.otf", sz, -4), top=(245, 248, 250), bot=(110, 112, 118), depth=0.06, angle=40,
                                     ext=(60, 60, 66), ext_far=(18, 18, 20), spec=0.75, noise=6, glow=((255, 255, 255), 30 * k, 0.18))
    A8["unmasked"] = metal("UNMASKED", 300); A8["demons"] = metal("DEMONS", 340); A8["armageddon"] = metal("ARMAGEDDON", 400)
    A8["mask"] = metal("MASK", 600); A8["necro"] = metal("NECROMANCER", 260)


def word_row(canvas, items, t, x0, y, size, gapk=0.30, op=1.0):
    """items = [(layer, t_on)], left-aligned on baseline-ish centre y; each word rises in at its time."""
    x = x0
    for (pm, a), t_on in items:
        w_ = a.shape[1]; pad = a.shape[0] * 0.18
        if t >= t_on:
            u = clamp((t - t_on) / 0.14); X.place(canvas, pm, a, x + w_ / 2, y + (1 - out_cubic(u)) * 10 * K, 1.0, 0, u * op)
        x += w_ - 2 * pad + size * gapk * K
    return x


def row_w(items, size, gapk=0.30):
    x = 0.0
    for (pm, a), _ in items: x += a.shape[1] - 2 * a.shape[0] * 0.18 + size * gapk * K
    return x - size * gapk * K


def caption(canvas, rows, t, x0, y0, t_box, f=1.0):
    """narration box sized to its rows. rows = [(items, size, line_h)] ; y0 = centre of the first row."""
    if t < t_box: return
    wmax = max(row_w(it, sz) for it, sz, _ in rows); hh = sum(lh for _, _, lh in rows[1:]) * K
    s0 = rows[0][1] * K; s1 = rows[-1][1] * K
    nbox(canvas, x0 - P(34), y0 - s0 * 0.72, x0 + wmax + P(30), y0 + hh + s1 * 0.70, t_box, t, f)
    y = y0
    for it, sz, lh in rows:
        y += 0 if it is rows[0][0] else 0
    y = y0
    for i, (it, sz, lh) in enumerate(rows):
        if i: y += lh * K
        word_row(canvas, it, t, x0, y, sz, op=f)


def nbox(canvas, x0, y0, x1, y1, t_on, t, op=1.0):
    """manga narration box: black, thin chartreuse frame, scales in."""
    if t < t_on: return
    u = out_back(clamp((t - t_on) / 0.16), 2.2); cx, cy = (x0 + x1) / 2, (y0 + y1) / 2; hw, hh = (x1 - x0) / 2 * u, (y1 - y0) / 2 * u
    if hw < 2: return
    p0, p1 = (int(cx - hw), int(cy - hh)), (int(cx + hw), int(cy + hh))
    if op >= 0.999: cv2.rectangle(canvas, p0, p1, (8, 8, 10), -1)
    else:
        roi = canvas[max(0, p0[1]):p1[1], max(0, p0[0]):p1[0]]; roi[:] = (roi.astype(np.float32) * (1 - op) + 8 * op).astype(np.uint8)
    cv2.rectangle(canvas, p0, p1, tuple(int(c * op) for c in YEL), max(1, int(2 * K)), cv2.LINE_AA)


def jp_pop(canvas, L, t, t_on, x, y, rot=0.0, life=0.5, s0=1.0):
    if not (t_on <= t < t_on + life): return
    u = (t - t_on); e = out_back(clamp(u / 0.10), 2.6); f = clamp((t_on + life - t) / 0.08)
    jx, jy = X.shake(t, 4 * K, t_on)
    X.place(canvas, *L, x + jx, y + jy, s0 * (0.4 + 0.6 * e), rot, f)


def pop(canvas, L, t, t_on, x, y, rot=0.0, life=0.34, s0=1.0):
    if not (t_on <= t < t_on + life): return
    e = out_back(clamp((t - t_on) / 0.12), 2.0); f = clamp((t_on + life - t) / 0.07)
    X.place(canvas, *L, x, y, s0 * e * (1 + 0.04 * (t - t_on)), rot, clamp(e * 2) * f)


# ======================================================================== INTRO 0 - 6.11: the manga page that asks his name
PAGE = (10, 9, 11)
PAN = dict(A=dict(pts=[(70, 54), (1846, 30), (1862, 450), (56, 488)], t0=0.81, shot="H1b", look="manga", fr=(0, -620), f=(0.56, 0.44), z=1.05),
           B=dict(pts=[(56, 548), (936, 520), (918, 1048), (44, 1042)], t0=2.74, shot="H2", look="manga", fr=(-1150, 40), f=(0.5, 0.5), z=1.0),
           C=dict(pts=[(990, 516), (1866, 494), (1876, 1048), (972, 1054)], t0=4.67, shot="H3", look="manga", fr=(1150, -40), f=(0.5, 0.42), z=1.0))


def intro_page(t):
    page = np.empty((H, W, 3), np.uint8); page[:] = PAGE
    for key in ("A", "B", "C"):
        p = PAN[key]
        if t < p["t0"]: continue
        u = (t - p["t0"]) / 0.30; e = out_back(clamp(u), 1.4); dx, dy = p["fr"][0] * K * (1 - e), p["fr"][1] * K * (1 - e)
        pts = X.xform_pts(PTS(p["pts"]), s=lerp(1.08, 1.0, clamp(u)), rot=3.0 * (1 - clamp(u)), dx=dx, dy=dy)
        look = p["look"]
        cont = fit_into(src(p["shot"], t, look), pts, p["z"], *p["f"])
        if key == "A":                                    # concentration lines on the opening eye
            cx_, cy_ = pts.mean(0); fl = X.focus_lines(H, W, cx_ + 60 * K, cy_, X.on2(t), n=70, r_in=0.40, r_jit=0.20, width=(0.0012, 0.005))
            X.paint(cont, INKC, fl * 0.7)
        if key == "C" and t >= 5.02:                      # "...Shinoyama": colour floods back into him
            col = fit_into(src("H3", t, "raw"), pts, p["z"], *p["f"]); cx_, cy_ = pts.mean(0)
            r = out_cubic((t - 5.02) / 0.36) * 1.2 * math.hypot(*(pts.max(0) - pts.min(0))) / 2
            cont = cont.copy(); comp_full(cont, col, circ_mask(cx_, cy_ - 60 * K, r, feather=10 * K))
        X.panel(page, cont, pts, border=max(2, int(7 * K)), bcol=(244, 244, 246))
    # Polka breaks out of his panel
    if t >= 5.02:
        p = PAN["C"]; pts = PTS(p["pts"]); img, m = srcm("H3", t)
        img = fit_into(img, pts, p["z"], *p["f"]); m = fit_into(m, pts, p["z"], *p["f"], border=cv2.BORDER_CONSTANT)
        u = out_cubic((t - 5.02) / 0.40); x0_, y0_ = np.asarray(pts).min(0); x1_, y1_ = np.asarray(pts).max(0)
        stick_full(page, img, m, px=7, col=WHITE, px2=4, col2=INKC, shadow=(10, 10, 14, 0.6), s=lerp(1.0, 1.10, u), ax=(x0_ + x1_) / 2, ay=y1_, dy=-14 * K * u)
    return page


def scene_intro(t, n):
    if t < 0.81:
        canvas = cv2.convertScaleAbs(render_shot(SH["ST"], t), alpha=0.50); canvas = R7.cut_glitch(canvas, t, (0.21,), 0.12)
    else:
        page = intro_page(t)
        # page camera: slow drift, then the push into his panel
        cC = np.asarray(PTS(PAN["C"]["pts"])).mean(0); drift = 0.012 * math.sin(t * 0.9)
        s_ = 1.0 + 0.03 * smooth((t - 0.81) / 4.0); cx_, cy_ = W / 2, H / 2; rot = 0.6 * math.sin(t * 0.7)
        if t >= 5.02:
            u = ease_in((t - 5.02) / 1.09, 2.6); s_ = lerp(s_, 2.35, u); cx_ = lerp(W / 2, cC[0], smooth(u * 1.4)); cy_ = lerp(H / 2, cC[1] - 80 * K, smooth(u * 1.4)); rot = lerp(rot, -2.0, u)
        M = cv2.getRotationMatrix2D((float(cx_), float(cy_)), rot, s_ + drift); M[0, 2] += W / 2 - cx_; M[1, 2] += H / 2 - cy_
        canvas = cv2.warpAffine(page, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=PAGE)
        canvas = R7.cut_glitch(canvas, t, (0.81, 2.74, 4.67), 0.07, 0.6)
    w = DW["intro"]; z = A8["zz"]
    if 0.30 <= t < 2.45:                          # Misaki: "Can you say your own name?"
        f = clamp((2.45 - t) / 0.12); y0 = P(560) if t >= 0.81 else P(880)
        caption(canvas, [([(z[k_], w[i][0] + 0.30) for i, k_ in enumerate(("CAN", "YOU", "SAY", "YOUR", "OWN", "NAME?"))], 78, 0)], t, P(90), y0, 0.30, f)
    if 2.45 <= t < 4.05:                          # Polka: "The body that I'm in right now,"
        f = clamp((4.05 - t) / 0.12)
        caption(canvas, [([(z[k_], w[6 + i][0]) for i, k_ in enumerate(("THE", "BODY", "THAT"))], 78, 0),
                         ([(z[k_], w[9 + i][0]) for i, k_ in enumerate(("I\u2019M", "IN", "RIGHT", "NOW,"))], 78, 100)], t, P(110), P(600), 2.45, f)
    if 4.05 <= t < 5.92:                          # "its name is Polka Shinoyama."
        f = clamp((5.92 - t) / 0.12)
        caption(canvas, [([(z[k_], w[13 + i][0]) for i, k_ in enumerate(("ITS", "NAME", "IS"))], 78, 0), ([(A8["polka"], w[16][0])], 132, 120),
                         ([(A8["shino"], w[17][0])], 132, 135)], t, P(90), P(585), 4.05, f)
    if t >= 5.80: canvas = cv2.addWeighted(canvas, 1.0, np.full_like(canvas, 255), smooth((t - 5.80) / 0.31), 0)   # into his white shirt -> the logo
    return canvas


def ease_in(u, p=3): u = clamp(u); return u ** p


# ======================================================================== VERSE 8.03 - 16.13
def tone_field(bg, dot, pitch=9.0, grad=(0.05, 0.85), d=(0.6, 0.8), shape="dot", key=None):
    k_ = ("tf", bg, dot, pitch, grad, d, shape, W)
    return _lru(_LC, k_, lambda: X.tone_bg(H, W, bg, dot, pitch * K + 1, 45, grad, d, shape), 40).copy()


def v_skull(t):                                   # 8.03-8.74: out of the skull's eye socket, bone duotone + boiling lines + ゴゴゴ
    canvas = src("V1", t, "duo_bone")
    tone = A8["rt"] if "rt" in A8 else X.radial_tone(H, W, W * 0.5, H * 0.45, (0, 0, 0), (30, 24, 150), 8 * K + 1, 0.25, 1.0)
    A8["rt"] = tone; canvas = cv2.add(cv2.convertScaleAbs(canvas, alpha=0.92), cv2.convertScaleAbs(tone, alpha=0.9))
    fl = X.focus_lines(H, W, W * 0.5, H * 0.46, X.on2(t), n=90, r_in=0.42, r_jit=0.25); X.paint(canvas, INKC, fl * 0.85)
    for i, (tt, x, y, r) in enumerate(((8.03, 1460, 300, -8), (8.27, 1580, 560, 6), (8.50, 1450, 820, -4))):
        jp_pop(canvas, A8["go"], t, tt, P(x), P(y), r, life=8.74 - tt)
    return canvas


def v_face(t):                                    # 8.74-9.46: FACE behind the skull cut-out on a crimson tone field
    canvas = tone_field((28, 18, 120), (8, 6, 30), 9.0, (0.05, 0.95), (0.7, 0.7))
    dt = t - 8.74; e = expo_o(dt / 0.14); pm, a = A8["face"]
    X.place(canvas, pm, a, P(470) + (1 - e) * P(-60), P(560), lerp(1.35, 1.0, e) * 0.88 * (1 + 0.03 * dt), -2, clamp(dt / 0.05))
    img, m = srcm("V2", t, "duo_bone", zm=1.0)
    u = out_back(clamp(dt / 0.26), 1.6)
    stick_full(canvas, img, m, px=0, shadow=(14, -18, 22, 0.7), dx=lerp(P(780), P(560), u), dy=P(20), rot=lerp(8, 2, u), echoes=((-34, 0, (40, 30, 235), 0.9, 1.0),))
    return canvas


def expo_o(u): return out_expo(u)


def v_f2f(t):                                     # 9.46-10.43: face to face - split VS panel, Polka | the skull
    dt = t - 9.46; u = out_back(clamp(dt / 0.24), 1.3); swap = t >= 9.94
    L = tone_field((150, 120, 20), (60, 30, 6), 8.0, (0.1, 0.9), (1, 0.3)); R = tone_field((30, 20, 150), (10, 6, 50), 8.0, (0.1, 0.9), (-1, 0.3))
    img, m = srcm("PF", t, "raw", zm=1.05)
    stick_full(L, img, m, px=6, col=WHITE, shadow=(10, 12, 12, 0.6), dx=-P(330), dy=P(30), s=0.92)
    sk = src("SKe", t, "duo_red", zm=1.25); sk = cv2.addWeighted(sk, 1.0, R, 0.35, 0)
    R = cv2.addWeighted(R, 0.35, sk, 0.9, 0)
    # diagonal seam
    sx = (1 - u) * W * 0.62
    xa, xb = W * 0.56 - P(40 if swap else 0), W * 0.44 - P(40 if swap else 0)
    pl = [(-sx, 0), (xa - sx, 0), (xb - sx, H), (-sx, H)]; pr = [(xa + sx, 0), (W + sx, 0), (W + sx, H), (xb + sx, H)]
    canvas = np.empty((H, W, 3), np.uint8); canvas[:] = (8, 8, 10)
    X.panel(canvas, X.warp_to(L, 1.0, 0, -sx, 0, border=cv2.BORDER_REPLICATE), pl, border=0)
    X.panel(canvas, X.warp_to(R, 1.0, 0, sx, 0, border=cv2.BORDER_REPLICATE), pr, border=0)
    cv2.line(canvas, (int(xa), 0), (int(xb), H), WHITE, max(2, int(12 * K)), cv2.LINE_AA)
    for i, tt in enumerate((9.46, 9.60, 9.74)):
        if t >= tt:
            e = out_back(clamp((t - tt) / 0.12), 2.2); L_ = A8["f2f"][i]
            X.place(canvas, *L_, W * 0.5 + P((-30, 0, 30)[i]), H * 0.5 + P((i - 1) * 175), e * 0.92, 8)
    if 9.94 <= t < 9.98: canvas = X.impact_frames(canvas, t, 9.94, 2, 60)
    return canvas


def v_knight(t):                                  # 10.43-11.38: Shagrua inked into a manga panel; his sword arm breaks the border
    canvas = tone_field(PAPER, (40, 40, 44), 7.0, (0.0, 0.55), (0, 1))
    dt = t - 10.43; u = out_back(clamp(dt / 0.22), 1.5)
    pts = X.xform_pts(PTS([(160, 120), (1500, 70), (1560, 960), (110, 1010)]), s=lerp(1.2, 1.0, u), rot=lerp(-6, -2, u))
    img, m = srcm("V4", t, "manga", zm=1.0); cont = fit_into(img, pts, 1.0); mm = fit_into(m, pts, 1.0, border=cv2.BORDER_CONSTANT)
    sl = X.speed_lines(H, W, X.on2(t), angle=-28, n=60, length=(0.3, 0.9), thick=(1, 4)); X.paint(cont, INKC, sl * 0.6)
    X.panel(canvas, cont, pts, border=max(3, int(10 * K)), bcol=INKC)
    small = X.xform_pts(PTS([(1560, 140), (1830, 120), (1850, 520), (1580, 540)]), dy=(1 - out_back(clamp((t - 10.89) / 0.2))) * P(-700))
    if t >= 10.89: X.panel(canvas, fit_into(src("V4", 10.43 + 0.95 * 0.9, "manga_r"), small, 2.2, 0.60, 0.35), small, border=max(3, int(8 * K)), bcol=INKC)
    stick_full(canvas, cont, mm, px=7, col=WHITE, px2=0, s=1.04, dx=P(40), dy=-P(10))
    return canvas


def v_misaki(t):                                  # 11.38-12.35: the smile ... UNMASKED
    if t < 11.68:                                 # a sweet little panel
        canvas = tone_field((200, 170, 236), (160, 120, 210), 10.0, (0.1, 0.6), (0, 1))
        u = out_back(clamp((t - 11.38) / 0.18), 1.8); pts = X.xform_pts(PTS([(520, 170), (1400, 150), (1420, 910), (500, 930)]), s=u * 0.98 + 0.02, rot=4 * (1 - u))
        X.panel(canvas, fit_into(src("V5a", t), pts, 1.08, 0.5, 0.42), pts, border=max(3, int(10 * K)), bcol=WHITE)
        return canvas
    dt = t - 11.68
    canvas = tone_field((40, 30, 225), (10, 8, 12), 9.0, (0.05, 0.9), (0.6, 0.8))
    fl = X.focus_lines(H, W, W * 0.42, H * 0.42, X.on2(t), n=130); X.paint(canvas, (10, 8, 12), fl * 0.85)
    # UNMASKED in perspective behind her, slams in
    e = out_expo(dt / 0.16); pm, a = A8["unmasked"]; h_, w_ = a.shape; s_ = P(1250) / w_
    q = np.float32([(P(1060), P(250)), (P(1890), P(180)), (P(1905), P(410)), (P(1035), P(530))]); cq = q.mean(0); q = (q - cq) * lerp(1.5, 1.0, e) + cq
    draw_plane(canvas, pm, a, q, clamp(dt / 0.05))
    img, m = srcm("V5b", t, "raw")
    stick_full(canvas, img, m, px=9, col=WHITE, px2=5, col2=INKC, shadow=(10, 18, 22, 0.7), rot=-3 + 2 * math.sin(dt * 6), s=lerp(1.12, 1.0, out_cubic(dt / 0.3)),
               dx=-P(260), echoes=((-150, 0, WHITE, 0.45, 1.0), (-75, 0, INKC, 0.7, 1.0)))
    return canvas


def v_fire(t):                                    # 12.35-13.28: ARMAGEDDON burnt into the battlefield, sliced into strips
    dt = t - 12.35; img = src("V6", t, "raw"); canvas = img.copy(); pm, a = A8["armageddon"]
    X.place(canvas, pm, a, W * 0.5, H * 0.56, (W * 1.18) / a.shape[1] * (1 + 0.025 * dt), 0, clamp(dt / 0.06))
    R7.lum_through(canvas, img, 205, 40)
    n_ = 7; k1 = 1 - out_expo(dt / 0.30); k2 = (1 - out_expo((t - 12.82) / 0.22)) if t >= 12.82 else 0.0
    offs = [((-1) ** i) * P(900) * k1 * (1 + 0.25 * (i % 3)) + ((-1) ** (i + 1)) * P(110) * k2 for i in range(n_)]
    return X.strips(canvas, n_, 20, offs, gap=max(2, int(10 * K)), gapcol=(6, 6, 8), bg=np.zeros_like(canvas))


def v_tears(t):                                   # 13.28-14.26: the dead children inked on a cold page; TEARS fall out of the panel
    dt = t - 13.28; canvas = tone_field((60, 30, 14), (150, 90, 40), 8.0, (0.0, 0.7), (0, 1)); u = out_back(clamp(dt / 0.22), 1.4)
    p1 = X.xform_pts(PTS([(300, 80), (1640, 56), (1676, 800), (262, 836)]), s=lerp(1.2, 1.0, u), rot=lerp(4, 1, u))
    X.panel(canvas, fit_into(src("V7", t, "manga_b"), p1, 1.15, 0.5, 0.56), p1, border=max(3, int(9 * K)), bcol=WHITE)
    if t >= 13.74:
        x = W * 0.5 - P(330)
        for i, L in enumerate(A8["tears"]):
            d = max(0.0, t - 13.74 - i * 0.06); y = H * 0.80 + 0.5 * 1500 * K * d * d; f = clamp(d / 0.05) * clamp(1 - (y - H * 0.80) / (H * 0.32))
            if d > 0: X.place(canvas, *L, x, y, 1.0, (i - 2) * 6 * d * 4, f)
            x += L[1].shape[1] * 0.78
    return canvas


def v_army(t):                                    # 14.26-15.21: the skeleton army as a violet-toned manga spread
    dt = t - 14.26; canvas = np.empty((H, W, 3), np.uint8); canvas[:] = (8, 8, 10)
    img = src("V8", t, "manga_v"); u = out_back(clamp(dt / 0.22), 1.3)
    p1 = X.xform_pts(PTS([(40, 40), (1880, 40), (1880, 690), (40, 760)]), dy=(1 - u) * P(-900))
    X.panel(canvas, img, p1, border=max(3, int(8 * K)), bcol=WHITE)
    for j, (tt, pts, fx_, fy_, z_) in enumerate(((14.72, [(40, 800), (930, 730), (930, 1040), (40, 1040)], 0.30, 0.62, 2.4),
                                                (14.96, [(990, 726), (1880, 740), (1880, 1040), (990, 1040)], 0.62, 0.40, 2.8))):
        if t >= tt:
            uu = out_back(clamp((t - tt) / 0.16), 1.6); q = X.xform_pts(PTS(pts), s=lerp(1.3, 1.0, uu))
            X.panel(canvas, fit_into(src("V8", t, "manga_v"), q, z_, fx_, fy_), q, border=max(3, int(8 * K)), bcol=WHITE)
    for i, (tt, x, y, r) in enumerate(((14.26, 1640, 240, -10), (14.49, 1760, 470, 8), (14.72, 300, 260, -5))):
        jp_pop(canvas, A8["go"], t, tt, P(x), P(y), r, life=15.21 - tt, s0=0.8)
    return canvas


def v_eye(t):                                     # 15.21-16.13: DEMONS slams; the eye opens in a widening slit; dive into the drop
    dt = t - 15.21; canvas = np.empty((H, W, 3), np.uint8); canvas[:] = (6, 6, 8)
    hgt = lerp(P(170), H * 0.62, ease_in(clamp(dt / 0.80), 2.2)); y0, y1 = H / 2 - hgt / 2, H / 2 + hgt / 2
    eye = src("V9", t, "raw"); fl = X.focus_lines(H, W, W * 0.5, H * 0.5, X.on2(t, 24), n=80, r_in=0.30, r_jit=0.3); X.paint(eye, (250, 250, 250), fl * 0.35 * clamp((t - 15.72) / 0.2))
    X.panel(canvas, eye, [(0, y0), (W, y0), (W, y1), (0, y1)], border=max(2, int(4 * K)), bcol=WHITE)
    if dt < 0.55:
        e = out_expo(dt / 0.14); pm, a = A8["demons"]
        X.place(canvas, pm, a, W * 0.5, H * 0.5, lerp(1.6, 1.0, e) * (P(1400) / a.shape[1]), -3, clamp(dt / 0.04) * clamp((0.55 - dt) / 0.08))
    for tt in (15.72, 15.96):
        if tt <= t < tt + 0.05: canvas = cv2.addWeighted(canvas, 1.0, np.full_like(canvas, 255), 0.35, 0)
    if t >= 15.88:                                # pupil dive
        u = clamp((t - 15.88) / 0.25); canvas = iris_through(canvas, drop_first(16.135), W * 0.52, H * 0.5, u, ring=(255, 255, 255))
    return canvas


def drop_first(t): return src("D2b", t, "raw")


def scene_verse(t, n):
    if t < 8.74: return v_skull(t)
    if t < 9.46: return v_face(t)
    if t < 10.43: return v_f2f(t)
    if t < 11.38: return v_knight(t)
    if t < 12.35: return v_misaki(t)
    if t < 13.28: return v_fire(t)
    if t < 14.26: return v_tears(t)
    if t < 15.21: return v_army(t)
    return v_eye(t)


# ======================================================================== DROP 16.13 - 31.46
DP = [dict(t0=16.13, shot="D2b", look="manga_b", pts=[(36, 40), (1100, 64), (1046, 1044), (26, 1032)], fr=(0, 0), z=1.05, f=(0.5, 0.45)),
      dict(t0=16.85, shot="D1", look="manga_g", pts=[(1150, 40), (1886, 26), (1894, 506), (1124, 526)], fr=(900, -500), z=1.0, f=(0.5, 0.5)),
      dict(t0=17.57, shot="D3", look="manga_g", pts=[(1112, 572), (1890, 548), (1882, 1046), (1080, 1052)], fr=(800, 700), z=1.0, f=(0.4, 0.5)),
      dict(t0=18.30, shot="D4", look="raw", pts=[(-40, 640), (1960, 300), (1960, 520), (-40, 900)], fr=(-2200, 0), z=1.0, f=(0.5, 0.5))]


def drop_page(t):
    page = np.empty((H, W, 3), np.uint8); page[:] = (6, 6, 8)
    for i, p in enumerate(DP):
        if t < p["t0"]: continue
        u = clamp((t - p["t0"]) / 0.20); e = out_back(u, 1.5)
        pts = X.xform_pts(PTS(p["pts"]), s=lerp(1.35 if i == 0 else 1.15, 1.0, out_expo(u)), dx=p["fr"][0] * K * (1 - e), dy=p["fr"][1] * K * (1 - e))
        cont = fit_into(src(p["shot"], t, p["look"]), pts, p["z"], *p["f"])
        if i == 0:
            fl = X.focus_lines(H, W, *pts.mean(0), X.on2(t), n=100, r_in=0.30, r_jit=0.2); X.paint(cont, INKC, fl * 0.75)
        if i == 3:
            sl = X.speed_lines(H, W, X.on2(t, 24), angle=-9, n=50); X.paint(cont, WHITE, sl * 0.5)
        X.panel(page, cont, pts, border=max(3, int(9 * K)), bcol=WHITE)
    return page


def d_past(t):
    if t < 19.01:
        canvas = drop_page(t)
        jp_pop(canvas, A8["don"][0], t, 16.13, P(430), P(520), -8, life=0.62, s0=1.6)          # ドン on the drop
        jp_pop(canvas, A8["don"][1], t, 16.25, P(860), P(640), 6, life=0.50, s0=1.6)
        if t < 16.17: canvas = X.impact_frames(canvas, t, 16.13, 2, 60)
        return canvas
    # 19.01: the page is torn apart - the dragon, inked, in a big slanted panel
    dt = t - 19.01; dr = tone_field((60, 20, 10), (200, 120, 40), 9.0, (0.0, 0.85), (0.3, 1))
    pts = X.xform_pts(PTS([(90, 70), (1830, 40), (1860, 1010), (60, 1040)]), s=lerp(1.12, 1.0, out_expo(dt / 0.2)), rot=lerp(-3, -1, clamp(dt / 0.9)))
    cont = src("D5", t, "manga_b"); fl = X.focus_lines(H, W, W * 0.62, H * 0.42, X.on2(t), n=110, r_in=0.30); X.paint(cont, INKC, fl * 0.6)
    X.panel(dr, fit_into(cont, pts, 1.0), pts, border=max(3, int(9 * K)), bcol=WHITE)
    if dt < 0.30:
        k = out_cubic(dt / 0.30); pg = drop_page(19.0)
        offs = [((-1) ** i) * H * 1.3 * k * (0.7 + 0.3 * (i % 2)) for i in range(6)]
        return X.strips(pg, 6, 70, offs, gap=0, bg=dr)
    return dr


def d_rebirth(t):
    if t < 20.40:                                 # the light pillar, white-out
        canvas = src("D6", t, "raw"); fl = X.focus_lines(H, W, W * 0.5, H * 0.35, X.on2(t), n=90, r_in=0.18); X.paint(canvas, (255, 255, 255), fl * 0.5)
        return cv2.addWeighted(canvas, 1.0, np.full_like(canvas, 255), smooth((t - 20.12) / 0.28), 0)
    if t < SH["R2"]["t0"]:
        canvas = src("R1", t, "duo_gold"); canvas = cv2.addWeighted(canvas, 1.0, np.full_like(canvas, 255), 1 - smooth((t - 20.40) / 0.35), 0)
        R7.ring_on_circle(canvas, t); return canvas
    if t < SH["R2"]["t0"] + 0.50:
        ca = R4.reinc_circle(t); bx, by, bz = R4.to_screen(SH["R2"], t, ZERO_ACC, 0.545, 0.36)
        canvas = circle_match(src("R1", t, "duo_gold"), r2_frame(t), ca, (bx, by, 0.05 * W * bz), (t - SH["R2"]["t0"]) / 0.50); R7.ring_on_circle(canvas, t); return canvas
    if t < 21.95: return r2_frame(t)
    if t < 22.27:
        ex, ey, _ = R4.to_screen(SH["R2"], t, ZERO_ACC, 0.545, 0.36); return iris_through(r2_frame(t), ghosts(t), ex, ey, (t - 21.95) / 0.32, ring=(200, 120, 255))
    if t < 22.86: return ghosts(t)
    # 22.86-23.81: Polka in colour, cut out of an inked ghost crowd
    dt = t - 22.86; bg = src("D10", t, "manga_v"); bg = cv2.addWeighted(bg, 0.85, tone_field((40, 6, 30), (120, 30, 90), 9.0), 0.25, 0)
    fl = X.focus_lines(H, W, W * 0.5, H * 0.45, X.on2(t), n=90, r_in=0.36); X.paint(bg, INKC, fl * 0.6)
    img, m = srcm("D10", t, "raw"); u = out_cubic(dt / 0.6)
    stick_full(bg, img, m, px=8, col=WHITE, px2=4, col2=(120, 30, 160), shadow=(12, 14, 16, 0.6), s=lerp(1.0, 1.14, u), ay=H, dy=-P(10),
               echoes=((-50, 0, (160, 40, 200), 0.5, 1.02), (50, 0, (40, 30, 235), 0.35, 1.04)))
    return bg


def r2_frame(t):                                 # his eye: a sticker on a cold screentone field
    bg = tone_field((120, 70, 20), (230, 200, 150), 8.0, (0.05, 0.75), (-0.7, 0.7))
    sl = X.speed_lines(H, W, X.on2(t), angle=0, n=40, length=(0.2, 0.6), thick=(1, 3)); X.paint(bg, (250, 250, 250), sl * 0.4)
    img, m = srcm("R2", t, "raw")
    if m.max() == 0: return img
    stick_full(bg, img, m, px=8, col=WHITE, px2=4, col2=INKC, shadow=(10, 14, 16, 0.5))
    return bg


def ghosts(t):                                    # the ghost crowd as a violet two-panel page
    c = tone_field((40, 8, 30), (130, 40, 110), 8.0, (0.0, 0.8), (0, 1))
    p1 = PTS([(50, 60), (1250, 40), (1200, 1030), (40, 1040)])
    X.panel(c, fit_into(src("D9", t, "manga_v"), p1, 1.0, 0.45, 0.5), p1, border=max(3, int(9 * K)), bcol=WHITE)
    if t >= 22.50:
        u2 = out_back(clamp((t - 22.50) / 0.16), 1.6); p2 = X.xform_pts(PTS([(1290, 120), (1880, 100), (1870, 980), (1270, 1000)]), s=lerp(1.3, 1.0, u2))
        X.panel(c, fit_into(src("D9", t, "duo_vio"), p2, 2.4, 0.72, 0.45), p2, border=max(3, int(9 * K)), bcol=WHITE)
    return c


def d_cafe(t):
    if t < 24.53:                                 # Lemmings, bandaged face: red duotone with stuttering red echoes
        dt = t - 23.81; c = tone_field((10, 8, 40), (40, 30, 200), 9.0, (0.0, 0.9), (0.5, 1))
        half = int(dt / (BEAT8 / 2)); sg = (1 if half % 2 else -1) * (1 if dt < 0.5 else 0)
        pts = X.xform_pts(PTS([(240, 80), (1680, 50), (1720, 1000), (200, 1030)]), s=lerp(1.2, 1.0, out_expo(dt / 0.2)), dx=P(22) * sg, rot=1.2 * sg)
        cont = fit_into(src("W1", t, "duo_red", zm=1.05), pts, 1.0); fl = X.focus_lines(H, W, *np.asarray(pts).mean(0), X.on2(t), n=110, r_in=0.30)
        X.paint(cont, (40, 30, 225), fl * 0.55); X.panel(c, cont, pts, border=max(3, int(9 * K)), bcol=WHITE)
        for i, (tt, x, y, r) in enumerate(((23.81, 1760, 230, -8), (24.05, 1800, 520, 6), (24.29, 1760, 810, -4))):
            jp_pop(c, A8["go"], t, tt, P(x), P(y), r, life=24.53 - tt, s0=0.75)
        return R6.glitch_hits(c, t, 23.81)
    if 24.74 <= t < 25.09: return R6.shatter(l2(t), l3(t), (t - 24.74) / 0.35, (0.50, 0.45))
    if t < 24.74: return l2(t)
    if t < 25.25: return l3(t)
    if t < 25.97: return vs_split(t)
    if t < 26.70:                                 # Polka shouting, sticker on teal focus lines
        dt = t - 25.97; bg = tone_field((150, 130, 20), (40, 30, 8), 8.0, (0.1, 0.9), (0.4, 1)); fl = X.focus_lines(H, W, W * 0.45, H * 0.40, X.on2(t), n=120, r_in=0.30)
        X.paint(bg, (12, 10, 8), fl * 0.8); img, m = srcm("L5", t, "raw", zm=1.0); jx, jy = X.shake(t, P(10) * math.exp(-dt / 0.2), 3)
        stick_full(bg, img, m, px=8, col=WHITE, px2=4, col2=INKC, shadow=(10, 14, 18, 0.6), dx=jx, dy=jy, s=lerp(1.15, 1.02, out_expo(dt / 0.25)),
                   echoes=((60, 0, (40, 30, 225), 0.6, 1.03),))
        return bg
    # 26.70: Lemmings in his violet light, sliced
    dt = t - 26.70; canvas = src("L6", t, "raw"); n_ = 5; k1 = 1 - out_expo(dt / 0.28)
    offs = [((-1) ** i) * P(700) * k1 for i in range(n_)]
    canvas = X.strips(canvas, n_, -14, offs, gap=max(2, int(8 * K)), gapcol=(6, 6, 8), bg=np.zeros_like(canvas))
    if t < 26.74: canvas = X.impact_frames(canvas, t, 26.70, 2, 60)
    return canvas


def l2(t):
    c = src("L2", t, "manga_r"); sl = X.speed_lines(H, W, X.on2(t, 24), angle=-12, n=55); X.paint(c, INKC, sl * 0.55); return c


def l3(t): return src("L3", t, "manga_r")


def vs_split(t):                                  # Polka | Lemmings, VS
    dt = t - 25.25; u = out_back(clamp(dt / 0.20), 1.4); beat2 = t >= 25.61
    L = tone_field((150, 120, 20), (50, 30, 6), 8.0, (0.1, 0.9), (1, 0.3)); R = tone_field((30, 20, 150), (8, 6, 40), 8.0, (0.1, 0.9), (-1, 0.3))
    img, m = srcm("L5", 25.97 + 0.1, "raw"); stick_full(L, img, m, px=6, col=WHITE, dx=-P(380), s=0.95)
    R = cv2.addWeighted(R, 0.3, X.warp_to(src("W1", 23.81 + 0.3, "duo_red"), 1.0, 0, P(360), 0), 0.85, 0)
    sx = (1 - u) * W * 0.6; off = P(30) if beat2 else 0
    xa, xb = W * 0.55 + off, W * 0.45 + off
    pl = [(-sx, 0), (xa - sx, 0), (xb - sx, H), (-sx, H)]; pr = [(xa + sx, 0), (W + sx, 0), (W + sx, H), (xb + sx, H)]
    canvas = np.empty((H, W, 3), np.uint8); canvas[:] = (8, 8, 10)
    X.panel(canvas, X.warp_to(L, 1.0, 0, -sx, 0, border=cv2.BORDER_REPLICATE), pl, border=0)
    X.panel(canvas, X.warp_to(R, 1.0, 0, sx, 0, border=cv2.BORDER_REPLICATE), pr, border=0)
    cv2.line(canvas, (int(xa), 0), (int(xb), H), WHITE, max(2, int(12 * K)), cv2.LINE_AA)
    if t >= 25.33: e = out_back(clamp((t - 25.33) / 0.12), 2.4); X.place(canvas, *A8["vs"], W * 0.5 + off, H * 0.5, e, -8)
    return canvas


def d_spell(t):
    if t < 28.36:                                 # the spell: beam with speed lines + zoom echo
        dt = t - 27.65; c = tone_field((40, 14, 6), (170, 100, 30), 9.0, (0.0, 0.8), (-0.4, 1)); u = out_back(clamp(dt / 0.2), 1.4)
        pts = X.xform_pts(PTS([(70, 140), (1850, 60), (1860, 940), (60, 1020)]), s=lerp(1.2, 1.0, u), rot=lerp(-5, -2, u))
        cont = src("S1", t, "manga_b"); sl = X.speed_lines(H, W, X.on2(t, 24), angle=-35, n=60); X.paint(cont, INKC, sl * 0.5)
        X.panel(c, fit_into(cont, pts, 1.0), pts, border=max(3, int(9 * K)), bcol=WHITE); return c
    if t < 28.62:                                 # mirrored circles
        c = src("S2", t, "manga_b"); c[:, W // 2:] = cv2.flip(c[:, :W // 2], 1)[:, :W - W // 2]; return c
    if t < 28.92:                                 # KATON-style black card
        dt = t - 28.62; c = np.empty((H, W, 3), np.uint8); c[:] = (4, 4, 6); pm, a = A8["necro"]
        X.place(c, pm, a, W * 0.5, H * 0.5, (P(1380) / a.shape[1]) * (1 + 0.05 * dt), 0, clamp(dt / 0.03)); return c
    if t < 29.81:                                 # the Corpse God over Polka: blue manga panel, the pair break out
        dt = t - 28.92; canvas = tone_field((30, 14, 8), (140, 80, 20), 9.0, (0.0, 0.8), (0, 1))
        u = out_back(clamp(dt / 0.2), 1.4); pts = X.xform_pts(PTS([(220, 90), (1700, 60), (1740, 1000), (180, 1030)]), s=lerp(1.25, 1.0, u), rot=lerp(5, 1.5, u))
        img, m = srcm("S4", t, "manga_b"); cont = fit_into(img, pts, 1.0); mm = fit_into(m, pts, 1.0, border=cv2.BORDER_CONSTANT)
        X.panel(canvas, cont, pts, border=max(3, int(10 * K)), bcol=WHITE)
        col, mc = srcm("S4", t, "raw"); col = fit_into(col, pts, 1.0); mc = fit_into(mc, pts, 1.0, border=cv2.BORDER_CONSTANT)
        k_ = smooth((t - 29.08) / 0.3); stick_full(canvas, col if k_ > 0.5 else cont, mm, px=6, col=WHITE, s=lerp(1.0, 1.06, k_), ay=H, dy=-P(8))
        return canvas
    if t < 30.55:                                 # the skull's red eye in a widening slit
        dt = t - 29.81; c = np.empty((H, W, 3), np.uint8); c[:] = (6, 6, 8); hgt = lerp(P(200), H * 0.75, out_cubic(dt / 0.74))
        y0, y1 = H / 2 - hgt / 2, H / 2 + hgt / 2; X.panel(c, src("S5", t, "manga_rg"), [(0, y0), (W, y0), (W, y1), (0, y1)], border=max(2, int(4 * K)), bcol=WHITE)
        for i, (tt, x, y, r) in enumerate(((29.81, 1640, 200, -8), (30.05, 1760, 470, 6), (30.30, 1640, 760, -4))):
            jp_pop(c, A8["go"], t, tt, P(x), P(y), r, life=30.55 - tt, s0=0.8)
        return c
    return finale8(t)


def finale8(t):                                   # 30.55-31.46: his real face, echoes, the character card
    s = SH["F6"]; dt = t - s["t0"]
    bg = tone_field((50, 18, 8), (170, 100, 34), 9.0, (0.0, 0.85), (0, 1))
    fl = X.focus_lines(H, W, W * 0.5, H * 0.42, X.on2(t), n=100, r_in=0.36); X.paint(bg, INKC, fl * 0.5)
    sc = lerp(0.42, 0.46, clamp(dt / 0.9)); a_ = smooth((dt - 0.04) / 0.25)
    if a_ > 0.01:
        shape = cv2.cvtColor(R4.skull_layer("SKa", SH["SKa"]["t0"] + 0.05, sc, W * 0.5, H * 0.20), cv2.COLOR_BGR2GRAY)
        shape = cv2.GaussianBlur(shape, (0, 0), 5 * K + 0.5).astype(np.float32) / 255.0
        bg = np.clip(bg.astype(np.float32) * ((1.0 - a_) + a_ * (0.34 + 0.9 * shape))[..., None], 0, 255).astype(np.uint8)
        bg = cv2.add(bg, cv2.convertScaleAbs(R4.glow_only(R4.skull_layer("SKb", SH["SKb"]["t1"] - 0.01, sc, W * 0.5, H * 0.20, pal=None), 1.2), alpha=a_))
    img, m = srcm("F6", t, "raw", zm=1.04)
    stick_full(bg, img, m, px=8, col=WHITE, px2=4, col2=INKC, shadow=(12, 14, 18, 0.6),
               echoes=((-70, 0, (40, 30, 225), 0.55 * clamp(1 - dt / 0.6), 1.02), (70, 0, WHITE, 0.30 * clamp(1 - dt / 0.6), 1.04)))
    if t < 30.59: bg = X.impact_frames(bg, t, 30.55, 2, 60)
    e = out_expo((dt - 0.10) / 0.16); y = H * 0.74
    if dt >= 0.10:
        pm, a = A8["t_name"]; X.place(bg, pm, a, W * 0.5, y + (1 - e) * P(24), lerp(1.10, 1.0, e), 0, clamp((dt - 0.10) / 0.06))
        u2 = clamp((dt - 0.30) / 0.15); pm, a = A8["t_sub"]; X.place(bg, pm, a, W * 0.5, y + P(104) + (1 - out_cubic(u2)) * P(10), 1.0, 0, u2)
        pm, a = A8["t_fine"]; X.place(bg, pm, a, W * 0.5, y + P(196), 1.0, 0, u2 * 0.9)
    return bg


def scene_drop(t, n):
    if t < 19.96: c = d_past(t)
    elif t < 23.81: c = d_rebirth(t)
    elif t < 27.65: c = d_cafe(t)
    else: c = d_spell(t)
    for i, wt in enumerate(tl.WHAT):              # the song's "What?" ad-libs
        x, y, r = R7.WHAT_POS[i % len(R7.WHAT_POS)]
        pop(c, A8["what"][i % 2], t, wt, W * x, H * y, r, 0.34, 0.85)
    return c


# ======================================================================== OUTRO 31.46 - 40.55
def o_mirror(t):                                  # the mirror as a split panel: Polka | his reflection, inked, turning into the skull
    dt = t - 31.46; u = out_back(clamp(dt / 0.26), 1.3)
    L = tone_field((150, 120, 20), (60, 30, 6), 8.0, (0.1, 0.9), (1, 0.3))
    img, m = srcm("O1a", t, "raw"); stick_full(L, img, m, px=6, col=WHITE, shadow=(10, 12, 12, 0.6), dx=-P(330), s=0.95)
    k = smooth((t - 31.90) / 0.9); rp = cv2.flip(src("O1a", t, "manga_v"), 1); rs = src("O1b", t, "manga_v", zm=1.6)
    R = cv2.addWeighted(rp, 1 - k, rs, k, 0)
    sx = (1 - u) * W * 0.6; xa, xb = W * 0.55, W * 0.45
    pl = [(-sx, 0), (xa - sx, 0), (xb - sx, H), (-sx, H)]; pr = [(xa + sx, 0), (W + sx, 0), (W + sx, H), (xb + sx, H)]
    c = np.empty((H, W, 3), np.uint8); c[:] = (8, 8, 10)
    X.panel(c, X.warp_to(L, 1.0, 0, -sx, 0, border=cv2.BORDER_REPLICATE), pl, border=0)
    X.panel(c, X.warp_to(R, 1.0, 0, sx, 0, border=cv2.BORDER_REPLICATE), pr, border=0)
    cv2.line(c, (int(xa), 0), (int(xb), H), WHITE, max(2, int(12 * K)), cv2.LINE_AA)
    if t >= 33.04:
        f = clamp((t - 33.04) / 0.14); y = H * 0.80
        X.place(c, *R7.X7["mir_l"], W * 0.25, y, 1.0, 0, f); X.place(c, *R7.X7["mir_r"], W * 0.75, y, 1.0, 0, f * 0.8)
    return c


def o_card(t):                                    # I don't even recognize myself - the hands inked in a tilted panel, lyric in a narration box
    dt = t - 33.46; c = tone_field((22, 18, 20), (58, 50, 56), 8.0, (0.0, 0.5), (0, 1)); u = out_back(clamp(dt / 0.22), 1.4)
    pts = X.xform_pts(PTS([(250, 40), (1670, 24), (1700, 590), (220, 616)]), s=lerp(1.2, 1.0, u), rot=lerp(-4, -1.5, u))
    X.panel(c, fit_into(src("O2", t, "manga"), pts, 1.0, 0.5, 0.52), pts, border=max(3, int(9 * K)), bcol=WHITE)
    if t >= 33.90:
        f = clamp((35.39 - t) / 0.12); z = A8["zz"]
        caption(c, [([(z["I"], 33.90), (z["DON\u2019T"], 33.96), (z["EVEN"], 34.12)], 78, 0), ([(A8["recog"], 34.46)], 150, 105),
                    ([(A8["myself"], 34.88)], 150, 128)], t, P(300), P(690), 33.90, f)
    return R7.cut_glitch(c, t, (34.46,), 0.08)


def o_vanish(t):                                  # I feel like I've disappeared - he breaks into screentone dots
    dt = t - 35.39; bg = tone_field((22, 18, 20), (58, 50, 56), 8.0, (0.0, 0.5), (0, 1))
    img, m = srcm("O3", t, "raw")
    L = X.to_layer(img, m)
    if L is not None:
        if t < 36.10: X.place(bg, L["pm"], L["a"], L["cx"], L["cy"])
        else:
            key = ("dis", fidx(SH["O3"], 36.10))
            if A8.get("dis_k") != key:
                img0, m0 = srcm("O3", 36.10, "raw"); L0 = X.to_layer(img0, m0); A8["dis"] = (X.Dissolve(L0["pm"], L0["a"], 9.0 * K + 1, sweep=(1.0, -0.4)), L0["cx"], L0["cy"]); A8["dis_k"] = key
            D, cx, cy = A8["dis"]; D.draw(bg, clamp((t - 36.10) / 1.05), cx, cy, 1.0, drift=(P(620), -P(300)))
    if t >= 35.88:
        f = clamp((37.27 - t) / 0.12); z = A8["zz"]
        caption(bg, [([(z["I"], 35.88), (z["FEEL"], 36.08), (z["LIKE"], 36.18), (z["I’VE"], 36.36)], 78, 0), ([(A8["disap"], 36.52)], 120, 112)],
                t, P(110), P(830), 35.88, f)
    return bg


def o_mask(t):                                    # the hood: inked, MASK behind him
    dt = t - 37.27; img = src("O4", t, "manga_dark"); c = img.copy()
    if t >= 37.88:
        d = t - 37.88; pm, a = A8["mask"]; X.place(c, pm, a, W * 0.56, H * 0.52, (W * 1.05 / a.shape[1]) * (1 + 0.03 * d), 0, clamp(d / 0.08) * 0.95)
        _, m = srcm("O4", t, "raw")
        if m.max() > 0: comp_full(c, img, m)
        else:
            g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32); fig = cv2.GaussianBlur(np.clip((110.0 - g) / 40.0, 0, 1), (0, 0), 2 * K + 0.5)
            comp_full(c, img, (fig * 255).astype(np.uint8))
    return c


def o_nothing(t):                                 # I got nothing - his face shrinks to one small panel on an empty page
    dt = t - 39.22; c = np.empty((H, W, 3), np.uint8); c[:] = (8, 8, 10); u = smooth((t - 39.60) / 0.9)
    s = lerp(1.0, 0.34, u); pts = X.xform_pts([(0, 0), (W, 0), (W, H), (0, H)], s=s, dy=-P(40) * u)
    X.panel(c, fit_into(src("O5", t, "manga"), pts, 1.0), pts, border=max(2, int(6 * K * u)), bcol=WHITE)
    if t >= 40.06:
        wn = row_w([(A8["nothing"], 0)], 110); caption(c, [([(A8["nothing"], 40.06)], 110, 0)], t, W * 0.5 - wn / 2, H * 0.82, 40.06, clamp((40.70 - t) / 0.15))
    return cv2.convertScaleAbs(c, alpha=1.0 - 0.85 * smooth((t - 40.30) / 0.40))


def scene_outro(t, n):
    if t < 33.46: return o_mirror(t)
    if t < 35.39: return o_card(t)
    if t < 37.27: return o_vanish(t)
    if t < 39.22: return o_mask(t)
    return o_nothing(t)


# ======================================================================== TAG: Lisa's line in the silence
def scene_tag8(t, n):
    full = X.manga(R7.scene_tag(t, n, ZERO_ACC), tone_col=VIO_T, keep_glow=1.0); c = tone_field((22, 18, 20), (58, 50, 56), 8.0, (0.0, 0.5), (0, 1))
    y0, y1 = H * 0.08, H * 0.64; pts = [(P(70), y0), (W - P(70), y0), (W - P(70), y1), (P(70), y1)]
    X.panel(c, fit_into(full, pts, 1.0, 0.5, 0.44), pts, border=max(2, int(3 * K)), bcol=(190, 190, 190))
    f = clamp((t - 40.62) / 0.3) * clamp((45.15 - t) / 0.12)
    X.place(c, *A8["cardlab"], P(70) + A8["cardlab"][1].shape[1] / 2, y0 - P(26), 1.0, 0, f * 0.8)
    return c


def tag_captions8(canvas, t):                     # Lisa's line in narration boxes, like the opening
    ws = [x[0] for x in DW["tag"]]; ws[0] = 40.84; L = R7.X7["tag"]; x0 = P(110); y0 = P(805)
    rows = lambda Ls, ts: [(l, tt) for l, tt in zip(Ls, ts)]
    if t < 41.92: caption(canvas, [(rows(L[0], ws[0:3]), 78, 0)], t, x0, y0, 40.84, clamp((41.92 - t) / 0.1))
    elif t < 43.90: caption(canvas, [(rows(L[1], ws[3:7]), 78, 0), (rows(L[2], ws[7:9]), 78, 100)], t, x0, y0, 41.92, clamp((43.90 - t) / 0.1))
    elif t < 45.15: caption(canvas, [(rows(L[3], ws[9:12]), 78, 0), (rows(L[4], ws[12:15]), 78, 100)], t, x0, y0, 43.90, clamp((45.15 - t) / 0.1))


# ======================================================================== hits, camera, post, dispatch
HITS = [(0.81, 0.4), (2.74, 0.4), (4.67, 0.4), (8.03, 0.6), (8.74, 0.9), (9.46, 0.8), (9.94, 0.6), (10.43, 0.9), (11.68, 1.0), (12.35, 0.9), (12.82, 0.5),
        (13.28, 0.4), (14.26, 0.8), (15.21, 1.0), (16.13, 1.5), (16.85, 1.0), (17.57, 1.0), (18.30, 1.0), (19.01, 1.2), (19.96, 0.8), (22.86, 0.8),
        (23.81, 1.0), (24.53, 0.8), (24.79, 1.2), (25.25, 0.9), (25.97, 1.0), (26.70, 1.3), (27.65, 1.0), (28.62, 1.1), (28.92, 0.9), (29.81, 0.8),
        (30.55, 1.4), (37.88, 0.5)]


def acc8(t):
    a = dict(zoom=0.0, shake=0.0, rgb=0.0, glow=0.0, flash=0.0)
    for h0, p in HITS:
        dt = t - h0
        if 0 <= dt < 0.6:
            a["zoom"] += 0.07 * p * math.exp(-dt / 0.08); a["shake"] += 13.0 * p * math.exp(-dt / 0.12)
            a["rgb"] += 3.0 * p * math.exp(-dt / 0.13); a["glow"] += 0.30 * p * math.exp(-dt / 0.14); a["flash"] += 0.10 * p * math.exp(-dt / 0.04)
    return a


def camera8(canvas, t, acc):
    dx, dy = X.shake(t, acc["shake"] * K, 1.7); rot = acc["shake"] * 0.02 * math.sin(t * 53); s = 1.0 + acc["zoom"]
    if tl.CHORUS <= t < tl.DROP_END:              # groove: bumps on the beat
        for i, b in enumerate(tl.B):
            d = t - b
            if 0 <= d < 0.28:
                e = math.exp(-d / 0.065) * math.sin(min(d / 0.05, 1.0) * math.pi / 2)
                if i % 2 == 0: dy += 9 * K * e
                else: dx += (8 if i % 4 == 1 else -8) * K * e
                rot += (0.45 if i % 4 < 2 else -0.45) * e; s += 0.010 * e
    if abs(dx) + abs(dy) + abs(rot) + abs(s - 1) < 0.02: return canvas
    s = max(s, 1.0 + 2.2 * (abs(dx) + abs(dy)) / W + 0.002)
    M = cv2.getRotationMatrix2D((W / 2, H / 2), rot, s); M[0, 2] += dx; M[1, 2] += dy
    return cv2.warpAffine(canvas, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)


def frame_at(n):
    t = n / FPS; acc = acc8(t); kw = dict(grain=0.07, glow0=0.06, vig=0.8, ca=True, streak=False, hal=False)
    if t < tl.LOGO_T[0]: canvas = scene_intro(t, n); kw.update(grain=0.08, ca=False)
    elif t < tl.LOGO_T[4]: canvas = R2.scene_logo(t, n); acc = dict(ZERO_ACC); kw.update(glow0=0.0, vig=0.0, ca=False, grain=0.05)
    elif t < tl.CHORUS: canvas = scene_verse(t, n)
    elif t < tl.DROP_END: canvas = scene_drop(t, n); kw.update(streak=True)
    elif t < 40.55: canvas = scene_outro(t, n)
    elif t < tl.CARD_T: canvas = scene_tag8(t, n); kw.update(grain=0.08)
    else: canvas = R7.scene_card(t, n); acc = dict(ZERO_ACC); kw.update(glow0=0.0, vig=0.0, ca=False, grain=0.04)
    canvas = R7.post7(canvas, t, acc, n, **kw)
    canvas = camera8(canvas, t, acc)
    if 40.55 <= t < tl.CARD_T: tag_captions8(canvas, t)
    R7.signature(canvas, t)
    return canvas


def worker(args):
    wi, n0, n1 = args
    out = f"{ROOT}/out/{MODE}8_part{wi}.mp4"
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
    # interleaved chunks so the heavy sections spread over all workers
    CH = max(1, int(FPS * 1.5)); chunks = [(n, min(n1, n + CH)) for n in range(n0, n1, CH)]
    jobs = [(i, a, b) for i, (a, b) in enumerate(chunks)]
    with mp.Pool(NW, initializer=setup8) as pool: parts = pool.map(worker, jobs, chunksize=1)
    with open(f"{ROOT}/out/{MODE}8_parts.txt", "w") as f:
        for p in parts: f.write(f"file '{p}'\n")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{ROOT}/out/{MODE}8_parts.txt", "-c", "copy", f"{ROOT}/out/{MODE}8_video.mp4"], check=True)
    for p in parts: os.remove(p)
    print("wrote", f"{ROOT}/out/{MODE}8_video.mp4", n1 - n0, "frames")
