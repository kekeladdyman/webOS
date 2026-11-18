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
    W6["high_v"] = rot(R5.serif("HIGH", 170, WHITE, SD)); W6["shin_v"] = rot(R5.vline("SHINJUKU", 150))
    W6["L_wide"] = letters("WIDE", SD[0], 240 * k, tracking=-2 * k, wght=(520, 72)); W6["L_far"] = letters("FAR", SD[0], 300 * k, tracking=-2 * k, wght=(520, 72))
    W6["valley"] = hv("VALLEY", 300, YEL, (20, 40, 40)); W6["low"] = R5.serif("LOW", 64, YEL, SD)
    W6["river"] = R5.serif("RIVER", 430, YEL, R5.SERIF, vcrop=True); W6["where"] = hv("WHERE", 300, CREAM, (30, 26, 34))
    W6["name"] = R5.serif("NAME", 96, YEL, SD, tracking=230)
    W6["misaki"] = R5.vline("MISAKI", 230); W6["lemmings"] = R5.vline("LEMMINGS", 120)
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
    put(canvas, pm, a, W * 0.5 - dt * 40 * K, H * 0.40, scale=lerp(1.5, 1.0, e) * (W * 0.94 / a.shape[1]), rot=-5, opacity=clamp(dt / 0.04))
    if m is not None: comp_matte(canvas, ink(img, "wb", 58), m)
    if t >= 9.58:
        u = (t - 9.58) / 0.5; pm, a = W6["high_v"]; put(canvas, pm, a, W * 0.045, H * (0.80 - 0.42 * out_cubic(u)), opacity=clamp(u * 6))
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
        text_plane(canvas, pm, a, Rmat(18, 0, 0), W * 0.22, H * 0.80, -40, lerp(1.6, 1.0, e), clamp(dt / 0.04), lroll=-7)
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
        slam(canvas, *T["c_high"], Rmat(24, 0, 0), W * 0.215, H * 0.56 - out_cubic(dt / 0.5) * H * 0.07, t, 31.97, lroll=-4, sy=1 + 0.9 * out_cubic(dt / 0.45), sc=0.46)
    return canvas


R4.scene_body = scene_body; R4.scene_spell = scene_spell


def frame_at(n):
    canvas = R4.frame_at(n); t = n / FPS
    if CLOSE <= t < 36.15:                           # the closing line, one word at a time, in the lower bar
        offs = (0.0, 0.12, 0.40, 0.64, 0.90, 1.12, 1.36, 1.58); f2 = clamp((36.15 - t) / 0.3); ov = 38 * K
        ws = T["d_close"]; x = W / 2 - (sum(a.shape[1] for pm, a in ws) - (len(ws) - 1) * ov) / 2; cy = H * (1 - 0.128 / 2)
        for (pm, a), off in zip(ws, offs):
            if t >= CLOSE + off:
                u = clamp((t - CLOSE - off) / 0.16); put(canvas, pm, a, x + a.shape[1] / 2, cy + (1 - out_cubic(u)) * 6 * K, opacity=u * f2)
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
