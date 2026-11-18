"""V4 renderer. usage: render4.py [draft|final] [t_start t_end] -> out/<mode>4_video.mp4
Opening reel, official logo, vow card and outro come from render2; everything from 8.22 to 33.6 is new (ink / colour, circle cuts, rhymes)."""
import os
os.environ["TLMOD"] = "tl4"
import subprocess, multiprocessing as mp
from r2core import *
import render2 as R2

SH = tl.BY
X = {}                      # extra assets (per worker)
FULL = [s for s in tl.SHOTS if s["mode"] == "full"]
WHITE = (248, 246, 244)


# ---------------------------------------------------------------- helpers
def cam(shot, t, acc=ZERO_ACC):
    d = shot["t1"] - shot["t0"]; u = clamp((t - shot["t0"]) / d)
    ue = out_cubic(u) * 0.6 + u * 0.4 if shot["punch"] > 0 else u
    zoom = max(1.0, lerp(shot["z"][0], shot["z"][1], ue) * (1 + acc["zoom"]))
    (x0, y0), (x1, y1) = shot["pan"]; lim = 0.5 * (1 - 1 / max(zoom, 1.0001))
    return zoom, clamp(lerp(x0, x1, ue), 0.5 - lim, 0.5 + lim), clamp(lerp(y0, y1, ue), 0.5 - lim, 0.5 + lim)


def to_screen(shot, t, acc, px, py):
    z, cx, cy = cam(shot, t, acc); return ((px - cx) * z + 0.5) * W, ((py - cy) * z + 0.5) * H, z


def fr(shot, t, acc=ZERO_ACC):
    """one finished frame of a shot: camera, grade, ink, light trails, mirror."""
    img = render_shot(shot, t, acc)
    if shot.get("echo"):
        img = img.copy()
        for k in range(1, shot["echo"] + 1):
            tp = t - k / 22.0
            if tp < shot["t0"]: break
            img = cv2.max(img, cv2.convertScaleAbs(render_shot(shot, tp, acc), alpha=0.74 ** k))
    if shot.get("mirror"):
        img = img.copy(); img[:, W // 2:] = img[:, :W // 2][:, ::-1]
    return img


def ink_cut(shot, t, acc, bg_pal="red", fg_pal="wb"):
    """figure in black-and-white ink, cut out over a flat coloured ink ground."""
    img, m = render_shot(shot, t, acc, want_matte=True)
    canvas = ink(img, bg_pal, 50)
    if m is not None: comp_matte(canvas, ink(img, fg_pal, 58), m)
    return canvas


def affine_place(img, s, rot, px, py, qx, qy):
    """rotate+scale about source point (px,py), then put that point at (qx,qy)."""
    M = cv2.getRotationMatrix2D((px, py), rot, s); M[0, 2] += qx - px; M[1, 2] += qy - py
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)


def poly_mask(pts):
    m = np.zeros((H, W), np.uint8); cv2.fillPoly(m, [np.array(pts, np.int32)], 255, cv2.LINE_AA); return m


# ---------------------------------------------------------------- rhymes: past life | this life
def diptych(t, L, Rr, fl, frr, t0, labels=True, sl=1.0, sr=1.0):
    """two slanted panels: left = past life (ink), right = this life (colour). fl/frr = subject points (normalised)."""
    canvas = np.zeros((H, W, 3), np.uint8)
    e = out_expo((t - t0 + 0.07) / 0.30); dr = (t - t0) * 26 * K; gap = 9 * K; sk = H * 0.5 * math.tan(math.radians(9))
    xm = W * 0.5
    for shot, f, side, s_ in ((L, fl, -1, sl), (Rr, frr, 1, sr)):
        img = fr(shot, t)
        pcx = W * (0.25 if side < 0 else 0.75)
        img = zoom_at(img, s_, f[0] * W, f[1] * H, pcx, H * 0.5 + side * dr, reflect=True)
        off = int(round(side * (1 - e) * H * -1.0))                     # left drops in from above, right rises from below
        if side < 0: pts = [(0, 0), (xm + sk - gap, 0), (xm - sk - gap, H), (0, H)]
        else: pts = [(xm + sk + gap, 0), (W, 0), (W, H), (xm - sk + gap, H)]
        m = poly_mask(pts)
        if off:
            Mt = np.float32([[1, 0, 0], [0, 1, off]]); img = cv2.warpAffine(img, Mt, (W, H)); m = cv2.warpAffine(m, Mt, (W, H))
        comp_matte(canvas, img, m)
    col = tuple(int(c * e) for c in WHITE); lw = max(1, int(round(2 * K)))
    cv2.line(canvas, (int(xm + sk - gap), 0), (int(xm - sk - gap), H), col, lw, cv2.LINE_AA)
    cv2.line(canvas, (int(xm + sk + gap), 0), (int(xm - sk + gap), H), col, lw, cv2.LINE_AA)
    if labels and e > 0.5:
        a_ = clamp((t - t0 - 0.12) / 0.2) * 0.92
        (kj, mn) = X["past"]; comp_pm(canvas, *kj, a_, int(W * 0.035), int(H * 0.86)); comp_pm(canvas, *mn, a_ * 0.9, int(W * 0.035 + kj[1].shape[1] + 12 * K), int(H * 0.86 + 12 * K))
        (kj, mn) = X["now"]; x = int(W * 0.965 - kj[1].shape[1]); comp_pm(canvas, *kj, a_, x, int(H * 0.075)); comp_pm(canvas, *mn, a_ * 0.9, int(x - mn[1].shape[1] - 12 * K), int(H * 0.075 + 12 * K))
    return canvas


def stare_down(t, top, bot, ft, fb, t0, beat2):
    """two horizontal strips: the eye that killed him, the eye that hunts him now."""
    canvas = np.zeros((H, W, 3), np.uint8)
    e = out_expo((t - t0 + 0.07) / 0.28); gap = 12 * K; sk = W * 0.5 * math.tan(math.radians(3.5)); ym = H * 0.5
    hit = math.exp(-(t - beat2) / 0.10) if t >= beat2 else 0.0
    for shot, f, side in ((top, ft, -1), (bot, fb, 1)):
        if t >= beat2 and t - beat2 < 3.2 / 60:                          # palette snaps on the second beat
            img = ink(render_shot(shot, t, raw=True), "red" if side > 0 else "bw", 50)
        else: img = fr(shot, t)
        s_ = 2.15 * (1 + 0.06 * hit) * (1 + 0.035 * (t - t0))                # v10: closer on the eyes
        img = zoom_at(img, s_, f[0] * W, f[1] * H, W * 0.5 - side * (t - t0) * 30 * K, H * (0.25 if side < 0 else 0.75), reflect=True)
        if side < 0: pts = [(0, 0), (W, 0), (W, ym - sk - gap), (0, ym + sk - gap)]
        else: pts = [(0, ym + sk + gap), (W, ym - sk + gap), (W, H), (0, H)]
        m = poly_mask(pts); off = int(round(side * (1 - e) * W))          # top slides in from the left, bottom from the right
        if off:
            Mt = np.float32([[1, 0, off], [0, 1, 0]]); img = cv2.warpAffine(img, Mt, (W, H)); m = cv2.warpAffine(m, Mt, (W, H))
        comp_matte(canvas, img, m)
    col = tuple(int(c * e) for c in WHITE); lw = max(1, int(round(2 * K)))
    cv2.line(canvas, (0, int(ym + sk - gap)), (W, int(ym - sk - gap)), col, lw, cv2.LINE_AA)
    cv2.line(canvas, (0, int(ym + sk + gap)), (W, int(ym - sk + gap)), col, lw, cv2.LINE_AA)
    return canvas


# ---------------------------------------------------------------- the body: 8.22 -> 28.55
def reinc_circle(t):
    """the big reincarnation circle in R1's source frame (it drifts and grows) -> screen (x, y, r)."""
    s = SH["R1"]; st = s["ss"] + (t - s["t0"])
    nx = 0.42 - 0.11 * (st - 531.3); ny = 0.50 + 0.04 * (st - 531.3)
    x, y, z = to_screen(s, t, ZERO_ACC, nx, ny); return x, y, 0.255 * W * z            # an inner ring that stays inside the frame


def scene_body(t, n, acc):
    # I1 — out of the eye socket the logo's "O" turned into
    if t < SH["I1"]["t1"]:
        s = SH["I1"]; e = out_expo((t - s["t0"]) / 0.42); img = render_shot(s, t)
        if e < 0.999: img = zoom_at(img, lerp(3.2, 1.0, e), 0.72 * W, 0.18 * H, lerp(0.5, 0.72, e) * W, lerp(0.5, 0.18, e) * H, reflect=True)
        return img
    if t < SH["I2"]["t1"]: return ink_cut(SH["I2"], t, acc)
    # I5: the palette flips on the half beat
    if SH["I5"]["t0"] <= t < SH["I5"]["t1"] and 11.52 <= t < 11.52 + 3.2 / 60: return ink(render_shot(SH["I5"], t, acc, raw=True), "bw", 58)
    # I6 -> I7: through Shagrua's eye
    if 12.20 <= t < 12.50:
        ex, ey, _ = to_screen(SH["I6"], t, acc, 0.49, 0.36)
        return iris_through(fr(SH["I6"], t, acc), fr(SH["I7a"], t), ex, ey, (t - 12.20) / 0.30, ring=(255, 150, 255))
    # R1 -> R2: the reincarnation circle lands on his eye
    if 16.45 <= t < 16.95:
        ca = reinc_circle(t); bx, by, bz = to_screen(SH["R2"], t, ZERO_ACC, 0.545, 0.36)
        return circle_match(fr(SH["R1"], t), fr(SH["R2"], t), ca, (bx, by, 0.05 * W * bz), (t - 16.45) / 0.50)
    if 16.95 <= t < SH["R2"]["t1"]: return fr(SH["R2"], t, acc)
    # rhymes
    if 19.50 <= t < 20.43: return diptych(t, SH["Q1L"], SH["Q1R"], (0.50, 0.50), (0.50, 0.47), 19.50)
    if 20.43 <= t < 21.34: return diptych(t, SH["Q2L"], SH["Q2R"], (0.56, 0.52), (0.50, 0.50), 20.43)
    # E1: the Evil Eye ignites; on the next beat the camera snaps in, then we fall through the pupil
    if SH["E1"]["t0"] <= t < 22.35:
        s = SH["E1"]; img = render_shot(s, t, acc); ex, ey, _ = to_screen(s, t, acc, 0.49, 0.40)
        if t >= 21.80:
            zz = 1.0 + 0.14 * out_expo((t - 21.80) / 0.14)
            img = zoom_at(img, zz, ex, ey, lerp(ex, W / 2, 0.7), lerp(ey, H / 2, 0.7), reflect=True)
            ex, ey = lerp(ex, W / 2, 0.7), lerp(ey, H / 2, 0.7)
        if t < 22.05: return img
        return iris_through(img, fr(SH["E2"], t), ex, ey, (t - 22.05) / 0.30, ring=(200, 120, 255))
    if SH["E4"]["t0"] <= t < SH["E4"]["t1"]: return ink_cut(SH["E4"], t, acc)
    if 24.15 <= t < 25.10: return stare_down(t, SH["Q3T"], SH["Q3B"], (0.49, 0.36), (0.44, 0.52), 24.15, 24.64)
    cur = [s for s in FULL if s["t0"] <= t < s["t1"]]
    return fr(cur[-1], t, acc) if cur else np.zeros((H, W, 3), np.uint8)


# ---------------------------------------------------------------- the spell: 30.58 -> 33.6
SK_EYES = {"SKa": ((0.50, 0.21), 0.34, 0.0), "SKb": ((0.567, 0.16), 0.335, 5.8)}      # eye midpoint, eye distance (of W), tilt


def skull_layer(name, t, scale_to, qx, qy, pal="wb"):
    (mx, my), dist, tilt = SK_EYES[name]
    img = render_shot(SH[name], t, raw=True)
    if pal: img = ink(img, pal, "otsu")
    return affine_place(img, scale_to / dist, tilt, mx * W, my * H, qx, qy)


def glow_only(img, gain=1.35):
    """just the saturated light of a frame (glowing eyes), ready to be added onto something else."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    k = np.clip((hsv[..., 1].astype(np.float32) - 95) / 50, 0, 1) * np.clip((hsv[..., 2].astype(np.float32) - 105) / 60, 0, 1)
    k = cv2.GaussianBlur(k, (0, 0), 3.0 * K + 0.5)[..., None]
    return np.clip(img.astype(np.float32) * k * gain, 0, 255).astype(np.uint8)


def split_face(t, acc):
    """left half the Corpse God's skull, right half the boy he lives in — eyes on one line. On the half beat the skull's eye lights."""
    ey = 0.43 * H; t_sk = SH["SKa"]["t0"] + 0.05
    sk = skull_layer("SKa", t_sk, 0.31, W * 0.5, ey)
    if t >= SH["SKb"]["t0"]:
        sk = cv2.add(sk, glow_only(skull_layer("SKb", t, 0.31, W * 0.5, ey, pal=None)))
    pf = ink(render_shot(SH["PF"], t, raw=True), "wb", 56)
    pf = affine_place(pf, 0.31 / 0.27, 0.0, 0.50 * W, 0.405 * H, W * 0.5, ey)
    canvas = sk.copy(); canvas[:, W // 2:] = pf[:, W // 2:]
    cv2.line(canvas, (W // 2, 0), (W // 2, H), WHITE, max(2, int(round(3 * K))), cv2.LINE_AA)
    z = 1.0 + 1.6 * acc["zoom"] + 0.05 * (t - SH["SKa"]["t0"])
    return zoom_at(canvas, z, W / 2, ey, W / 2 + acc["shake"] * K * noise1(t, 3.0), ey + acc["shake"] * K * noise1(t, 7.0), reflect=True)


def finale(t, acc):
    """Polka in the blue light; the light behind him takes the shape of the Corpse God's skull, and its eyes open."""
    s = SH["F6"]; dt = t - s["t0"]
    canvas = render_shot(s, t, acc).copy()
    fg, m = render_shot(s, t, acc, want_matte=True, zmul=1.045)
    a_ = smooth((dt - 0.06) / 0.32)
    if a_ > 0.01:
        sc = lerp(0.42, 0.46, clamp(dt / 1.05)); qx, qy = W * 0.5, H * 0.17
        shape = cv2.cvtColor(skull_layer("SKa", SH["SKa"]["t0"] + 0.05, sc, qx, qy), cv2.COLOR_BGR2GRAY)
        shape = cv2.GaussianBlur(shape, (0, 0), 5 * K + 0.5).astype(np.float32) / 255.0
        gain = (1.0 - a_) + a_ * (0.34 + 0.86 * shape)                                         # bone = light, sockets = shadow
        canvas = np.clip(canvas.astype(np.float32) * gain[..., None], 0, 255).astype(np.uint8)
        canvas = cv2.add(canvas, cv2.convertScaleAbs(glow_only(skull_layer("SKb", SH["SKb"]["t1"] - 0.01, sc, qx, qy, pal=None), 1.2), alpha=a_))
    if m is not None: comp_matte(canvas, fg, m)
    return canvas


def scene_spell(t, n, acc):
    if t >= SH["F6"]["t0"]: return finale(t, acc)
    if t >= SH["SKa"]["t0"]: return split_face(t, acc)
    cur = [s for s in FULL if s["t0"] <= t < s["t1"]]
    return fr(cur[-1], t, acc)


# ---------------------------------------------------------------- dispatch
def inked(t):
    """is the frame mostly ink right now? (keeps bloom and streaks off the flat whites)"""
    if 8.22 <= t < 12.42 or 13.42 <= t < 14.86 or 23.68 <= t < 28.31 or 28.55 <= t < tl.CHORUS: return True
    if 31.51 <= t < 31.97 or 32.44 <= t < 32.90: return True
    return False


def frame_at(n):
    t = n / FPS; acc = accents(t); grain = 0.085; glow0 = 0.10; vig = 1.0; ca = True; streak = True
    if t < 5.86: canvas = R2.scene_film(t, n); acc = ZERO_ACC; grain = 0.19
    elif t < 8.22: canvas = R2.scene_logo(t, n); acc = ZERO_ACC; glow0 = 0.0; vig = 0.0; ca = False; grain = 0.05
    elif t < 28.55: canvas = scene_body(t, n, acc)
    elif t < tl.CHORUS: canvas = R2.scene_pocket(t, n)
    elif t < 33.60: canvas = scene_spell(t, n, acc)
    else:
        canvas = R2.scene_outro(t, n, acc)
        if t >= 36.85: vig = clamp((37.45 - t) / 0.6); glow0 = 0.10 * vig; ca = t < 37.45; grain = 0.085 if t < 37.45 else 0.05
    if 8.22 <= t < 33.60 and inked(t): glow0 = 0.03; streak = False; vig = 0.55
    canvas = R2.post(canvas, t, acc, n, grain, glow0, vig, ca, streak)
    bar = int(round(tl.letterbox(t) * H))
    if bar > 0: canvas[:bar] = 0; canvas[H - bar:] = 0
    if t > tl.END - 0.30: canvas = cv2.convertScaleAbs(canvas, alpha=clamp((tl.END - t) / 0.30))
    return canvas


def setup():
    cv2.setNumThreads(1)
    R2.A = R2.Assets(); R2.FINALE_HOOK = finale
    k = K; mono = R2.A.mono; kj = lambda s_: layer(tmask(s_, "ZenAntique.ttf", 34 * k, tracking=4 * k), fill=WHITE, shadow=(6 * k, 0.6, 0, 3 * k))
    X["past"] = (kj("前世"), mono("PAST LIFE", 15)); X["now"] = (kj("今世"), mono("THIS LIFE", 15))


def worker(args):
    wi, n0, n1 = args; setup()
    out = f"{ROOT}/out/{MODE}4_part{wi}.mp4"
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
    with open(f"{ROOT}/out/{MODE}4_parts.txt", "w") as f:
        for p in parts: f.write(f"file '{p}'\n")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{ROOT}/out/{MODE}4_parts.txt", "-c", "copy", f"{ROOT}/out/{MODE}4_video.mp4"], check=True)
    print("wrote", f"{ROOT}/out/{MODE}4_video.mp4", n1 - n0, "frames")
