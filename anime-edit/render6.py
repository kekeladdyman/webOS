"""V6 renderer. usage: render6.py [draft|final] [t_start t_end] -> out/<mode>6_video.mp4
V4's scene language (eye and circle transitions, split panels, ink) + the reference fonts, with
  - fight transitions: slash wipes along the sword cuts, whip pushes
  - fire transitions: a burn that climbs the frame with an ember edge
  - words built into the scenes: behind cut-out figures, on the ground, up a building, on the seam between panels, cut by a sword."""
import os
os.environ["TLMOD"] = "tl4"
import subprocess, multiprocessing as mp
from r2core import *
import render2 as R2
import render4 as R4
import render5 as R5
from render2 import word_layer, with_shadow, text_plane, slam, CLOSE

SH = tl.BY; T = R5.T; fr = R4.fr
YEL, CREAM, VRED, WHITE = R5.YEL, R5.CREAM, R5.VRED, (248, 246, 244)
W6 = {}; _S = {}
_orig_body = R4.scene_body; _orig_spell = R4.scene_spell


def setup():
    R5.setup(); R2.FINALE_HOOK = finale; k = K; HV = R5.HEAVY; SD = R5.SERIF_D
    hv = lambda s_, sz, col, ex: layer(tmask(s_, HV[0], sz * k, tracking=-3 * k, wght=HV[1]), fill=col, extrude=(max(3, int(round(7 * k))), 1.0, 1.0, ex))
    rot = lambda L: (cv2.rotate(L[0], cv2.ROTATE_90_COUNTERCLOCKWISE), cv2.rotate(L[1], cv2.ROTATE_90_COUNTERCLOCKWISE))
    W6["mount"] = layer(tmask("MOUNTAIN", HV[0], 330 * k, tracking=-3 * k, wght=HV[1]), fill=(12, 6, 10))
    W6["high_v"] = rot(R5.vline("HIGH", 190)); W6["shin_v"] = rot(R5.vline("SHINJUKU", 150))
    _txt = "IF YOU NEED ME \u00b7 CALL ME \u00b7 NO MATTER WHERE YOU ARE \u00b7 NO MATTER HOW FAR \u00b7 "
    _st = tmask(_txt * 2, SD[0], 56 * k, tracking=8 * k, wght=(520, 72), vcrop=False); W6["ring"] = _st
    W6["L_wide"] = letters("WIDE", SD[0], 240 * k, tracking=-2 * k, wght=(520, 72)); W6["L_far"] = letters("FAR", SD[0], 300 * k, tracking=-2 * k, wght=(520, 72))
    W6["valley"] = hv("VALLEY", 300, YEL, (20, 40, 40)); W6["low"] = R5.serif("LOW", 64, YEL, SD)
    W6["river"] = layer(tmask("RIVER", SD[0], 470 * k, tracking=-4 * k, wght=(460, 72)), fill=CREAM, glow=((255, 200, 120), 18 * k, 0.45), shadow=(14 * k, 0.9, 0, 6 * k))
    W6["close"] = [R5.serif(w, 92, YEL, ("Newsreader.ttf", (420, 72))) for w in ("IT", "SEEMS", "THIS", "LAND", "I\u2019VE", "ARRIVED", "IN", "IS")]; W6["where"] = hv("WHERE", 300, CREAM, (30, 26, 34))
    W6["name"] = R5.serif("NAME", 96, YEL, SD, tracking=230)
    W6["misaki"] = R5.vline("MISAKI", 230); W6["lemmings"] = R5.vline("LEMMINGS", 175)
    empty = (np.zeros((2, 2, 3), np.uint8), np.zeros((2, 2), np.uint8))
    R4.X["past"] = (R5.serif("PAST LIFE", 44, WHITE, SD), empty); R4.X["now"] = (R5.serif("THIS LIFE", 44, WHITE, SD), empty)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); W6["xx"] = xx; W6["yy"] = yy; W6["ramp"] = (H - yy) / H


# ---------------------------------------------------------------- transitions that come out of the action
def sdist(ang):
    if ang not in _S:
        th = math.radians(ang)
        _S[ang] = ((W6["xx"] - W / 2) * -math.sin(th) + (W6["yy"] - H / 2) * math.cos(th), abs(W * math.sin(th)) / 2 + abs(H * math.cos(th)) / 2)
    return _S[ang]


def slash_wipe(A_, B_, u, ang):
    """a blade edge sweeps the frame; the next shot is behind it."""
    S, half = sdist(ang); pos = lerp(-half, half, smooth(u))
    m = np.clip((pos - S) / (3 * K) + 0.5, 0, 1)[..., None]
    out = A_.astype(np.float32) * (1 - m) + B_.astype(np.float32) * m
    out += np.exp(-((S - pos) / (9 * K)) ** 2)[..., None] * 255.0
    return np.clip(out, 0, 255).astype(np.uint8)


def slash_split(img, ang, amt):
    """the frame is cut in two along a line and the halves slip apart."""
    S, _ = sdist(ang); th = math.radians(ang); dx, dy = math.cos(th) * amt, math.sin(th) * amt
    a = cv2.warpAffine(img, np.float32([[1, 0, dx], [0, 1, dy]]), (W, H), borderMode=cv2.BORDER_REFLECT_101)
    b = cv2.warpAffine(img, np.float32([[1, 0, -dx], [0, 1, -dy]]), (W, H), borderMode=cv2.BORDER_REFLECT_101)
    out = np.where((S > 0)[..., None], a, b).astype(np.float32) + np.exp(-(S / (2.5 * K)) ** 2)[..., None] * 200.0
    return np.clip(out, 0, 255).astype(np.uint8)


def whip(A_, B_, u, d):
    """the hit shoves one shot out and the next one in."""
    e = smooth(u); dx, dy = d
    sh = lambda img, ox, oy: cv2.warpAffine(img, np.float32([[1, 0, ox], [0, 1, oy]]), (W, H), borderMode=cv2.BORDER_REFLECT_101)
    canvas = sh(A_, -e * W * dx, -e * H * dy); b = sh(B_, (1 - e) * W * dx, (1 - e) * H * dy)
    if dx > 0: x0 = int((1 - e) * W); canvas[:, x0:] = b[:, x0:]
    elif dx < 0: x1 = int(e * W); canvas[:, :x1] = b[:, :x1]
    elif dy > 0: y0 = int((1 - e) * H); canvas[y0:] = b[y0:]
    else: y1 = int(e * H); canvas[:y1] = b[:y1]
    kb = int(math.sin(math.pi * u) * 110 * K) | 1
    return cv2.blur(canvas, (kb, 1) if dx else (1, kb)) if kb > 2 else canvas


def fire_wipe(A_, B_, u, col):
    """fire climbs the frame and eats it; the next shot is underneath. col = ember colour."""
    f = R2.A.burn * 0.55 + W6["ramp"] * 0.45; thr = 1.12 * (1 - u) - 0.06
    m = np.clip((f - thr) / 0.03, 0, 1)[..., None]; edge = np.clip(1 - np.abs(f - thr) / 0.09, 0, 1)
    out = A_.astype(np.float32) * (1 - m) + B_.astype(np.float32) * m
    out += (edge ** 1.5)[..., None] * np.array(col, np.float32) * 1.1 + (edge ** 5)[..., None] * 230.0
    return np.clip(out, 0, 255).astype(np.uint8)


TR = [(10.54, "whip", "I3", "I4", 0.07, 0.06, (1, 0)), (13.42, "fire", "I7b", "I8", 0.16, 0.08, (255, 150, 60)),
      (13.89, "slash", "I8", "I9", 0.06, 0.07, -28), (14.37, "slash", "I9", "I10", 0.06, 0.07, 34),
      (26.47, "whip", "L1", "L2", 0.07, 0.06, (1, 0)), (26.91, "slash", "L2", "L3", 0.06, 0.07, 24),
      (27.38, "whip", "L3", "L4", 0.07, 0.06, (-1, 0)), (27.84, "slash", "L4", "L5", 0.06, 0.07, -30),
      (28.31, "fire", "L5", "L6", 0.12, 0.08, (255, 80, 220))]
TRS = [(31.05, "whip", "S1", "S2", 0.07, 0.06, (0, -1)), (31.51, "slash", "S2", "S3", 0.06, 0.07, 30), (31.97, "whip", "S3", "S4", 0.07, 0.06, (0, 1))]
KIND = {"whip": whip, "slash": slash_wipe, "fire": fire_wipe}


def trans_frame(t, acc, table):
    for tc, kind, an, bn, pre, post_, prm in table:
        if tc - pre <= t < tc + post_:
            return KIND[kind](fr(SH[an], t, acc), fr(SH[bn], t, acc), (t - (tc - pre)) / (pre + post_), prm)
    return None


# ---------------------------------------------------------------- shots with a word between the ground and the figure
def shot_i2(t, acc):
    """Shagrua: black type on the red ground, the white figure in front of it; a second word climbs the frame edge."""
    s = SH["I2"]; img, m = render_shot(s, t, acc, want_matte=True); canvas = ink(img, "red", 50)
    dt = t - s["t0"]; e = out_expo(dt / 0.14); pm, a = W6["mount"]
    put(canvas, pm, a, W * 0.305 - dt * 30 * K, H * 0.44, scale=lerp(1.5, 1.0, e) * (W * 0.47 / a.shape[1]), rot=-6, opacity=clamp(dt / 0.04))   # v2: in the cave, the sword crosses it
    if m is not None: comp_matte(canvas, ink(img, "wb", 58), m)
    if t >= 9.58:
        u = (t - 9.58) / 0.5; pm, a = W6["high_v"]; put(canvas, pm, a, W * 0.06, H * (0.78 - 0.30 * out_cubic(u)), opacity=clamp(u * 6))
    return canvas


def shot_e4(t, acc):
    """Misaki: her name on the red ground behind her."""
    s = SH["E4"]; img, m = render_shot(s, t, acc, want_matte=True); canvas = ink(img, "red", 50)
    dt = t - s["t0"]; e = out_expo(dt / 0.12); pm, a = W6["misaki"]
    put(canvas, pm, a, W * 0.50, H * 0.50, scale=lerp(1.4, 1.0, e) * (W * 0.92 / a.shape[1]), rot=-8, opacity=clamp(dt / 0.04))
    if m is not None: comp_matte(canvas, ink(img, "wb", 58), m)
    return canvas


def words_body(canvas, t, acc):
    if 11.03 <= t < 11.98:                           # painted on the ground under the skeleton army
        dt = t - 11.03; e = out_expo(dt / 0.16); pm, a = W6["valley"]
        text_plane(canvas, pm, a, Rmat(0, -64, 0), W * 0.5, H * 1.10 + (1 - e) * H * 0.3, 0, 1.25, clamp(dt / 0.05))
        if t >= 11.50:
            pm, a = W6["low"]; comp_pm(canvas, pm, a, clamp((t - 11.50) / 0.1), int(W * 0.955 - a.shape[1]), int(H * 0.90))
    if 12.59 <= t < 13.26:                           # too big for the frame: cut off by its bottom edge
        dt = t - 12.59; pm, a = W6["river"]; put(canvas, pm, a, W * 0.5 - dt * 120 * K, H * 0.955, opacity=clamp(dt / 0.08))
    if 13.12 <= t < 13.44:                           # letters pulled across the whole width
        ls, (tw, th) = W6["L_wide"]; sp = out_cubic((t - 13.12) / 0.3) * W * 0.15
        pm, a = word_layer(W6["L_wide"], CREAM, [((i - 1.5) * sp + tw * 0.75, 0.0, 1.0) for i in range(len(ls))], wmul=2.5)
        pm, a = with_shadow(pm, a, 12 * K, 0.95, 4 * K); put(canvas, pm, a, W * 0.5, H * 0.52)
    if 14.08 <= t < 14.86: slam(canvas, *T["enough_v"], Rmat(-26, 4, 0), W * 0.52, H * 0.60, t, 14.08, lroll=-4)
    if 17.72 <= t < 18.60:                           # climbing the side of the tower
        u = (t - 17.72) / 0.88; pm, a = W6["shin_v"]
        put(canvas, pm, a, W * 0.635, H * (0.60 - 0.14 * out_cubic(u)), opacity=clamp(u * 8) * clamp((18.60 - t) / 0.08))
    if 18.78 <= t < 19.50:                           # lying on the street
        dt = t - 18.78; e = out_expo(dt / 0.16); pm, a = W6["where"]
        text_plane(canvas, pm, a, Rmat(0, -66, 0), W * 0.5, H * 1.16 + (1 - e) * H * 0.3, 0, 1.3, clamp(dt / 0.05) * clamp((19.50 - t) / 0.06))
    if 20.50 <= t < 21.34:                           # one letter per life, one on the seam
        ls, (tw, th) = W6["L_far"]; sp = smooth((t - 20.50) / 0.7) * W * 0.14 + W * 0.10; offs = []
        for i in range(len(ls)):
            ui = (t - 20.50 - i * 0.05) / 0.16
            offs.append(((i - 1) * sp + tw * 1.0, (1 - out_back(ui)) * th * 0.3 if ui > 0 else th, clamp(ui * 3)))
        pm, a = word_layer(W6["L_far"], CREAM, offs, wmul=3.0); pm, a = with_shadow(pm, a, 12 * K, 0.95, 4 * K); put(canvas, pm, a, W * 0.5, H * 0.52)
    if 24.54 <= t < 25.10:                           # on the seam between the two eyes
        u = out_expo((t - 24.54) / 0.14); hb = 66 * K * u; dy = math.tan(math.radians(3.5)) * W / 2     # the seam opens into a black band
        cv2.fillPoly(canvas, [np.array([(0, H / 2 + dy - hb), (W, H / 2 - dy - hb), (W, H / 2 - dy + hb), (0, H / 2 + dy + hb)], np.int32)], (6, 4, 6), cv2.LINE_AA)
        pm, a = W6["name"]; put(canvas, pm, a, W * 0.5, H * 0.5, rot=-3.5, opacity=clamp((t - 24.56) / 0.12))
    if 25.60 <= t < 26.40:
        dt = t - 25.60; e = out_expo(dt / 0.12); pm, a = W6["lemmings"]
        text_plane(canvas, pm, a, Rmat(18, 0, 0), W * 0.25, H * 0.78, -40, lerp(1.6, 1.0, e), clamp(dt / 0.04), lroll=-7)
    if 26.50 <= t < 27.38:                           # thrown through the fight
        dt = t - 26.50; e = out_expo(dt / 0.16); pm, a = T["hurry"]; xoff = (1 - e) * W * 0.7 - dt * 40 * K
        if e < 0.97:
            kb = int((1 - e) * 120 * K) | 1; pm = cv2.blur(pm, (kb, 1)); a = cv2.blur(a, (kb, 1))
        text_plane(canvas, pm, a, Rmat(-20, 0, 0), W * 0.5 + xoff, H * 0.70, -40, 1.0, clamp(dt / 0.04) * clamp((27.38 - t) / 0.06), lroll=-3)
    if 28.07 <= t < 28.55:                           # ... struck out
        dt = t - 28.07; e = out_expo(dt / 0.12); pm, a = T["worry"]; cx, cy = W * 0.66, H * 0.68
        put(canvas, pm, a, cx, cy, scale=lerp(1.4, 1.0, e), rot=-4, opacity=clamp(dt / 0.04) * clamp((28.55 - t) / 0.05))
        if t >= 28.30:
            u = out_cubic((t - 28.30) / 0.13); half = a.shape[1] * 0.44; x0 = cx - half; x1 = x0 + 2 * half * u
            cv2.line(canvas, (int(x0), int(cy + 8 * K + half * 0.07)), (int(x1), int(cy + 8 * K + half * 0.07 - (x1 - x0) * 0.07)), VRED, max(3, int(22 * K)), cv2.LINE_AA)


def ring_text(canvas, cx, cy, r, ang0, a_):
    """v9: an incantation written around a magic circle (text bent onto a ring, rotating)."""
    if a_ <= 0.01 or r < 20 * K: return
    st = W6["ring"]; hs, ws = st.shape; band = hs * (r / (0.30 * W)) ** 0.0
    x0, x1 = int(max(0, cx - r - hs)), int(min(W, cx + r + hs)); y0, y1 = int(max(0, cy - r - hs)), int(min(H, cy + r + hs))
    if x1 - x0 < 4 or y1 - y0 < 4: return
    dx = W6["xx"][y0:y1, x0:x0 + (x1 - x0)] - cx; dy = W6["yy"][y0:y1, x0:x1] - cy
    rad = np.sqrt(dx * dx + dy * dy); th = np.arctan2(dy, dx)
    sx = (((th - ang0) / (2 * np.pi)) % 1.0) * ws; sy = (r + hs / 2 - rad) * (hs / band)
    m = cv2.remap(st, sx.astype(np.float32), sy.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    m = cv2.convertScaleAbs(m, alpha=a_); roi = canvas[y0:y1, x0:x1]
    band_m = np.clip(1.0 - np.abs(rad - r) / (hs * 0.62), 0, 1) ** 0.6 * 0.62 * a_          # a dark engraved band under the letters
    roi[:] = (roi.astype(np.float32) * (1 - band_m[..., None])).astype(np.uint8)
    glow = cv2.GaussianBlur(m, (0, 0), 6 * K + 0.5)
    roi[:] = cv2.add(roi, cv2.merge([cv2.convertScaleAbs(glow, alpha=0.30), cv2.convertScaleAbs(glow, alpha=0.62), cv2.convertScaleAbs(glow, alpha=0.95)]))
    comp_matte(roi, np.full_like(roi, (226, 240, 250)), m)


def scene_body(t, n, acc):
    if 21.22 <= t < 21.44:                           # the burning battlefield takes the whole frame, then his eye
        A_ = R4.diptych(min(t, 21.335), SH["Q2L"], SH["Q2R"], (0.56, 0.52), (0.50, 0.50), 20.43)
        return fire_wipe(A_, render_shot(SH["E1"], t, acc), (t - 21.22) / 0.22, (40, 140, 255))
    tf = trans_frame(t, acc, TR)
    if tf is not None: canvas = tf
    elif SH["I2"]["t0"] <= t < SH["I2"]["t1"]: canvas = shot_i2(t, acc)
    elif SH["E4"]["t0"] <= t < SH["E4"]["t1"]: canvas = shot_e4(t, acc)
    else: canvas = _orig_body(t, n, acc)
    words_body(canvas, t, acc)
    if 15.80 <= t < 16.95:                           # v9: the incantation rides the reincarnation circle, then shrinks with it onto his eye
        ca = R4.reinc_circle(min(t, 16.95)); ang = -0.9 * (t - 15.80) - 0.4
        if t < 16.45: x, y, rr = ca[0], ca[1], ca[2] * 0.64; a_ = clamp((t - 15.80) / 0.3)
        else:
            u = (t - 16.45) / 0.50; bx, by, bz = R4.to_screen(SH["R2"], t, ZERO_ACC, 0.545, 0.36); cb = (bx, by, 0.05 * W * bz)
            if u < 0.34: x, y, rr = ca[0], ca[1], ca[2] * 0.64
            else:
                e = smooth((u - 0.34) / 0.66); x = lerp(ca[0], cb[0], e); y = lerp(ca[1], cb[1], e); rr = ca[2] * 0.64 * ((cb[2] * 1.6) / (ca[2] * 0.64)) ** e
            a_ = 1.0 - smooth((u - 0.55) / 0.40)
        ring_text(canvas, x, y, rr, ang, a_)
    if 14.37 <= t < 14.86: canvas = slash_split(canvas, 34, (22 * math.exp(-(t - 14.37) / 0.22) + 5) * K)     # the sword cuts the word too
    return canvas


# ---------------------------------------------------------------- the spell
def finale(t, acc):
    """Polka in the blue light; the light behind him takes the shape of the skull; the last word stands behind him too."""
    s = SH["F6"]; dt = t - s["t0"]
    canvas = render_shot(s, t, acc).copy(); fg, m = render_shot(s, t, acc, want_matte=True, zmul=1.045)
    a_ = smooth((dt - 0.06) / 0.32)
    if a_ > 0.01:
        sc = lerp(0.42, 0.46, clamp(dt / 1.05)); qx, qy = W * 0.5, H * 0.17
        shape = cv2.cvtColor(R4.skull_layer("SKa", SH["SKa"]["t0"] + 0.05, sc, qx, qy), cv2.COLOR_BGR2GRAY)
        shape = cv2.GaussianBlur(shape, (0, 0), 5 * K + 0.5).astype(np.float32) / 255.0
        canvas = np.clip(canvas.astype(np.float32) * ((1.0 - a_) + a_ * (0.34 + 0.86 * shape))[..., None], 0, 255).astype(np.uint8)
        canvas = cv2.add(canvas, cv2.convertScaleAbs(R4.glow_only(R4.skull_layer("SKb", SH["SKb"]["t1"] - 0.01, sc, qx, qy, pal=None), 1.2), alpha=a_))
    e = out_expo(dt / 0.12); sc_ = lerp(1.5, 1.0, e) * (1 + 0.035 * dt)
    for (pm, a), sg in zip(T["c_en"], (-1, 1)):
        cx = W * 0.5 + sg * W * (0.288 + 0.10 * (1 - e)); cy = H * 0.40 - sg * W * 0.288 * 0.052
        put(canvas, pm, a, cx, cy, scale=sc_, rot=-3, opacity=clamp(dt / 0.03) * clamp((33.60 - t) / 0.22))
    if m is not None: comp_matte(canvas, fg, m)
    if t > 33.46: canvas = cv2.convertScaleAbs(canvas, alpha=clamp((33.60 - t) / 0.14))      # v2: dip to black before he speaks
    return canvas


def scene_spell(t, n, acc):
    if t >= SH["F6"]["t0"]: return finale(t, acc)
    if t >= SH["SKa"]["t0"]: return R4.split_face(t, acc)
    tf = trans_frame(t, acc, TRS); canvas = tf if tf is not None else _orig_spell(t, n, acc)
    if t < 31.05:
        slam(canvas, *T["c_aint"], Rmat(28, -5, 0), W * 0.38, H * 0.52, t, tl.CHORUS, lroll=-4)
    elif t < 31.51:
        dt = t - 31.05; sp = out_expo(dt / 0.16) * W * 0.20 + dt * 60 * K; R = Rmat(0, 16, 0)
        for (pm, a), sg in zip(T["c_no"], (-1, 1)):
            slam(canvas, pm, a, R, W * 0.5 + sg * (a.shape[1] * 0.36 + sp), H * 0.5, t, 31.05, lroll=sg * 3.0)
    elif t < 31.97:                                  # on the floor of the bar, under the skeleton
        dt = t - 31.51; e = out_expo(dt / 0.14)
        text_plane(canvas, *T["c_mount"], Rmat(0, -58, 0), W * 0.5, H * 1.02 + (1 - e) * H * 0.3, 0, 0.80, clamp(dt / 0.04))
    elif t < 32.44:
        dt = t - 31.97
        slam(canvas, *T["c_high"], Rmat(24, 0, 0), W * 0.215, H * 0.53 - out_cubic(dt / 0.5) * H * 0.07, t, 31.97, lroll=-4, sy=1 + 0.9 * out_cubic(dt / 0.45), sc=0.62)
    return canvas


def frame_lines(canvas, a_, m=0.035):
    """thin inset border with corner ticks (the MARATHON frame), drawn over a full-bleed shot."""
    if a_ <= 0.01: return
    col = tuple(int(c * a_) for c in CREAM); lw = max(1, int(round(1.6 * K))); x0, y0 = int(W * m), int(H * m * 16 / 9); x1, y1 = W - x0, H - y0
    ov = canvas.copy(); cv2.rectangle(ov, (x0, y0), (x1, y1), col, lw, cv2.LINE_AA); tk = int(24 * K); g = int(10 * K)
    for (x, y, sx, sy) in ((x0, y0, -1, -1), (x1, y0, 1, -1), (x1, y1, 1, 1), (x0, y1, -1, 1)):
        cv2.line(ov, (x + sx * g, y), (x + sx * (g + tk), y), col, lw, cv2.LINE_AA); cv2.line(ov, (x, y + sy * g), (x, y + sy * (g + tk)), col, lw, cv2.LINE_AA)
    cv2.addWeighted(ov, 1.0, canvas, 0.0, 0, dst=canvas)


def scene_pocket(t, n):
    """v4: the vow, full frame. Misaki in Lemmings' grip, the words stacked in the black of his cloak;
    then Polka's eyes, NO MATTER WHAT in red under them; the camera falls into the drop."""
    s1, s2 = SH["P1"], SH["P2"]; MID = tl.DLG_MID_T
    hb = sum(0.020 * math.exp(-(t - b) / 0.10) for b in (28.70, 28.98, 29.60, 29.88) if t >= b)
    if t < s2["t0"]:
        img = render_shot(s1, t); canvas = zoom_at(img, 1.0 + hb + 0.05 * (t - s1["t0"]), W * 0.40, H * 0.40, reflect=True)
        y = H * 0.635; x = W * 0.665
        for (pm, a), off in zip(T["d_prot"], (0.0, 0.50, 0.78)):
            if t >= MID + off:
                u = clamp((t - MID - off) / 0.18); put(canvas, pm, a, x + a.shape[1] / 2 + (1 - out_cubic(u)) * 18 * K, y, opacity=u)
            y += 112 * K
    else:
        g0 = tl.CHORUS - 0.50; grow = in_expo((t - g0) / 0.50) if t > g0 else 0.0
        img = render_shot(s2, t); canvas = zoom_at(img, 1.0 + hb + 0.9 * grow, W * 0.5, H * 0.60, reflect=True)
        ws = T["d_nmw"]; ov = 20 * K; x = W * 0.5 - (sum(a.shape[1] for pm, a in ws) - 2 * ov) / 2; sg = 1 + 0.6 * grow; yl = H * 0.875 + grow * H * 0.2
        for (pm, a), off in zip(ws, (1.10, 1.18, 1.44)):
            if t >= MID + off:
                u = t - MID - off; e2 = out_expo(u / 0.12); cxw = W * 0.5 + (x + a.shape[1] / 2 - W * 0.5) * sg
                put(canvas, pm, a, cxw, yl, scale=lerp(1.3, 1.0, e2) * sg, opacity=clamp(u / 0.04))
            x += a.shape[1] - ov
    frame_lines(canvas, 0.75 * clamp((t - s1["t0"]) / 0.3) * (1 - clamp((t - (tl.CHORUS - 0.35)) / 0.25)))
    return canvas


_orig_film = R2.scene_film


def scene_film(t, n):
    """v8: the reel, with single subliminal frames of what is coming spliced in on the intro's strongest beats."""
    canvas = _orig_film(t, n)
    for nm, t0, *_ in tl.FLASH:
        if t0 <= t < t0 + 1.0 / 24:
            A = R2.A; pw, ph = A.pw, A.ph; x0 = (W - pw) // 2; y0 = (H - ph) // 2
            pic = render_shot(SH[nm], t0, size=(pw, ph))
            canvas[y0:y0 + ph, x0:x0 + pw] = cv2.multiply(pic, A.film_vig, scale=1 / 255.0)
    return canvas


R2.scene_film = scene_film
_orig_post = R2.post


def post(img, t, acc, n, *args, **kw):
    """v10: film halation on the colour scenes - a warm glow bleeds around the brightest highlights."""
    out = _orig_post(img, t, acc, n, *args, **kw)
    if 8.22 <= t < 36.85 and not R4.inked(t) and not (tl.BY["SKa"]["t0"] <= t < tl.BY["F6"]["t0"]):
        sm = cv2.resize(out, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        lum = cv2.cvtColor(sm, cv2.COLOR_BGR2GRAY).astype(np.float32)
        hl = np.clip((lum - 218.0) / 37.0, 0, 1); hl = cv2.GaussianBlur(hl, (0, 0), W / 4 * 0.010) - cv2.GaussianBlur(hl, (0, 0), W / 4 * 0.002) * 0.6
        hl = np.clip(hl, 0, 1)
        hal = np.stack([hl * 16, hl * 40, hl * 105], -1).astype(np.float32)
        out = cv2.add(out, cv2.resize(hal, (W, H), interpolation=cv2.INTER_LINEAR).astype(np.uint8))
    return out


R2.post = post
R2.scene_pocket = scene_pocket
R4.scene_body = scene_body; R4.scene_spell = scene_spell


def frame_at(n):
    canvas = R4.frame_at(n); t = n / FPS
    if CLOSE - 0.15 <= t < 36.05:                    # the closing line, MARATHON-style: big thin serif, lower left, the second line on the bar edge
        f2 = clamp((36.05 - t) / 0.3); bar = tl.letterbox(t) * H
        k = clamp((t - (CLOSE - 0.15)) / 0.3) * f2 * 0.78
        g = np.clip(1.0 - np.hypot(W6["xx"] / (W * 0.70), (H - W6["yy"]) / (H * 0.62)), 0, 1)
        canvas = (canvas.astype(np.float32) * (1 - k * g)[..., None]).astype(np.uint8)
        offs = (0.0, 0.12, 0.40, 0.64, 0.90, 1.12, 1.36, 1.58); ov = 40 * K; ws = W6["close"]
        for li, (rng, y) in enumerate((((0, 4), H - bar - 92 * K), ((4, 8), H - bar - 4 * K))):
            x = W * 0.045
            for idx in range(*rng):
                pm, a = ws[idx]
                if t >= CLOSE + offs[idx]:
                    u = clamp((t - CLOSE - offs[idx]) / 0.16); put(canvas, pm, a, x + a.shape[1] / 2, y + (1 - out_cubic(u)) * 8 * K, opacity=u * f2)
                x += a.shape[1] - ov
    return canvas


def worker(args):
    wi, n0, n1 = args; setup()
    out = f"{ROOT}/out/{MODE}6_part{wi}.mp4"
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
    with open(f"{ROOT}/out/{MODE}6_parts.txt", "w") as f:
        for p in parts: f.write(f"file '{p}'\n")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{ROOT}/out/{MODE}6_parts.txt", "-c", "copy", f"{ROOT}/out/{MODE}6_video.mp4"], check=True)
    print("wrote", f"{ROOT}/out/{MODE}6_video.mp4", n1 - n0, "frames")
