"""V7 renderer: the edit rebuilt around SYNTHETIC. usage: render7.py [draft|final] [t0 t1] -> out/<mode>7_video.mp4"""
import os, json
os.environ["TLMOD"] = "tl7"
import subprocess, multiprocessing as mp
from r2core import *
import render2 as R2
import render4 as R4
import render5 as R5
import render6 as R6

SH = tl.BY; fr = R4.fr; T = R5.T
YEL, CREAM, VRED, WHITE = R5.YEL, R5.CREAM, R5.VRED, (248, 246, 244)
HUDC = (150, 236, 214)                 # HUD green-cream
X7 = {}
R2.LOGO_T = tl.LOGO_T
DW = json.load(open(f"{ROOT}/out/dlg7_words.json"))


# ======================================================================== assets
def setup():
    R6.setup(); k = K; A = R2.A; SD = R5.SERIF_D
    mono = lambda s_, sz=17, col=HUDC: layer(tmask(s_, "SpaceMono.ttf", sz * k, tracking=2.6 * k, vcrop=False), fill=col)
    X7["mono"] = mono
    hv = lambda s_, sz, col, ex, w=(900, 75): layer(tmask(s_, "ArchivoItalic.ttf", sz * k, tracking=-3 * k, wght=w), fill=col, extrude=(max(3, int(round(7 * k))), 1.0, 1.0, ex))
    sf_ = lambda s_, sz, col=YEL, w=SD[1]: layer(tmask(s_, SD[0], sz * k, tracking=-2 * k, wght=w, vcrop=False), fill=col, shadow=(9 * k, 0.75, 0, 4 * k))
    # HUD
    X7["h_file"] = mono("FILE 001  //  IDENTITY CHECK"); X7["h_rec"] = mono("REC", 17, (60, 60, 235))
    X7["h_prompt"] = tmask("> CAN YOU SAY YOUR OWN NAME?", "SpaceMono.ttf", 26 * k, tracking=2 * k, vcrop=False)
    X7["h_scan"] = mono("SCANNING SUBJECT", 15); X7["h_body"] = mono("BODY  //  NOT HIS OWN", 15)
    X7["h_name"] = tmask("NAME    POLKA SHINOYAMA", "SpaceMono.ttf", 21 * k, tracking=2.4 * k, vcrop=False)
    X7["h_stat"] = mono("STATUS  DECEASED", 21, (70, 60, 240)); X7["h_soul"] = mono("SOUL    UNKNOWN", 21)
    X7["h_mis"] = mono("IDENTITY  //  MISMATCH", 18, (70, 60, 240))
    # dialogue (MARATHON serif, word by word)
    X7["a1"] = [sf_(w, 118, YEL, (380, 72)) for w in ("THE", "BODY", "THAT", "I’M", "IN", "RIGHT", "NOW,")]
    X7["a2a"] = [sf_(w, 118, YEL, (380, 72)) for w in ("ITS", "NAME", "IS")]
    X7["a2b"] = [sf_(w, 176, YEL, (420, 72)) for w in ("POLKA", "SHINOYAMA.")]
    X7["tag"] = [[sf_(w, 84, YEL, (400, 72)) for w in ln] for ln in (("WHOEVER", "YOU", "ARE,"), ("IT", "SEEMS", "YOU’RE", "NOT"), ("POLKA", "SHINOYAMA,"),
                                                         ("AT", "LEAST", "NOT"), ("ON", "THE", "INSIDE."))]
    # verse
    X7["face3d"] = R5.jword("FACE", 330, "bone")
    fm = tmask("FACE", SD[0], 250 * k, tracking=-2 * k, wght=(420, 72)); X7["face_l"] = layer(fm, fill=YEL, stroke=((20, 14, 18), 3 * k), shadow=(12 * k, 0.9, 0, 5 * k))
    X7["face_r"] = layer(cv2.flip(fm, 1), fill=YEL, stroke=((20, 14, 18), 3 * k), shadow=(12 * k, 0.9, 0, 5 * k))
    X7["unmasked"] = R5.vline("UNMASKED", 250)
    X7["armageddon"] = layer(tmask("ARMAGEDDON", SD[0], 380 * k, tracking=-4 * k, wght=(430, 72)), fill=CREAM, glow=((80, 160, 255), 18 * k, 0.5), shadow=(14 * k, 0.9, 0, 6 * k))
    X7["L_tears"] = letters("TEARS", SD[0], 200 * k, tracking=4 * k, wght=(400, 72))
    X7["card_lab"] = mono("EP.01  \u00b7  16:43  \u00b7  THE DEAD", 14, CREAM); X7["card_idx"] = mono("N\u00b0 07", 14, CREAM)
    X7["demons"] = hv("DEMONS", 300, (40, 40, 230), (12, 6, 30))
    X7["synthetic"] = R5.jword("SYNTHETIC", 280, "cold")
    X7["what"] = R5.vline("WHAT?", 120)
    # title card (the JPOXI character card)
    X7["t_name"] = layer(tmask("POLKA SHINOYAMA", "Archivo.ttf", 150 * k, tracking=2 * k, wght=(900, 100)), fill=(246, 246, 246), glow=((255, 220, 200), 14 * k, 0.35), shadow=(12 * k, 0.8, 0, 6 * k))
    X7["t_sub"] = layer(tmask("THE CORPSE GOD", "Oswald.ttf", 54 * k, tracking=16 * k, wght=600), fill=(246, 246, 246), shadow=(8 * k, 0.7, 0, 3 * k))
    X7["t_sub2"] = mono("NECROMANCER  ·  REINCARNATED  ·  SHINJUKU", 15, (230, 230, 230))
    # outro
    mm = tmask("MIRROR", SD[0], 150 * k, tracking=-2 * k, wght=SD[1]); X7["mir_l"] = layer(mm, fill=CREAM, shadow=(9 * k, 0.75, 0, 4 * k))
    X7["mir_r"] = layer(cv2.flip(mm, 1), fill=(200, 210, 230), shadow=(9 * k, 0.6, 0, 4 * k))
    X7["recog"] = sf_("RECOGNIZE", 130); X7["myself"] = sf_("MYSELF", 130)
    X7["L_dis"] = letters("DISAPPEARED", SD[0], 120 * k, tracking=6 * k, wght=SD[1])
    X7["mask"] = layer(tmask("MASK", SD[0], 520 * k, tracking=-6 * k, wght=(500, 72)), fill=(30, 22, 26))
    X7["nothing"] = sf_("NOTHING", 96, CREAM, (420, 72))
    # signature (VRENS style) + billing block (JPOXI style)
    X7["sig"] = layer(tmask("SHIGAMI", "ArchivoItalic.ttf", 60 * k, tracking=-1 * k, wght=(900, 110)), fill=(236, 236, 236), shadow=(4 * k, 0.55, 0, 2 * k))
    dk = (32, 28, 30)
    X7["b1"] = layer(tmask("AN EDIT BY   SHIGAMI", "Oswald.ttf", 38 * k, tracking=12 * k, wght=600), fill=dk)
    X7["b2"] = layer(tmask("MUSIC  “SYNTHETIC”     FOOTAGE  DEAD MOUNT DEATH PLAY   EP. 01 · 02 · 04 · 05 · 12", "SpaceMono.ttf", 18 * k, tracking=2.5 * k, vcrop=False), fill=(70, 66, 68))
    X7["b3"] = layer(tmask("屍神", "ZenAntique.ttf", 42 * k, tracking=4 * k), fill=(38, 22, 206))
    # the incantation on the reincarnation circle, new words
    txt = "WHO ARE YOU · THIS BODY’S NAME IS POLKA SHINOYAMA · NOT ON THE INSIDE · "
    R6.W6["ring"] = tmask(txt * 2, SD[0], 56 * k, tracking=8 * k, wght=(520, 72), vcrop=False)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); X7["scan"] = ((yy.astype(np.int32) // max(2, int(3 * K))) % 2 == 0).astype(np.float32)


# ======================================================================== helpers
def reveal(mask, u):
    """type-on: show the first u (0..1) of a mask's width."""
    m = mask.copy(); m[:, int(m.shape[1] * clamp(u)):] = 0; return m


def cut_glitch(img, t, cuts, dur=0.09, amt=1.0):
    for c in cuts:
        dt = t - c
        if 0 <= dt < dur:
            k = (1 - dt / dur) * amt; rng = np.random.default_rng(int(c * 1000)); out = img.copy(); sh = int(16 * K * k)
            b, g, r = cv2.split(out); out = cv2.merge([np.roll(b, -sh, 1), g, np.roll(r, sh, 1)])
            for _ in range(int(3 + 4 * k)):
                y0 = int(rng.integers(0, H - 10)); hh = int(rng.integers(int(6 * K) + 2, int(50 * K) + 4)); out[y0:y0 + hh] = np.roll(out[y0:y0 + hh], int(rng.normal(0, 60 * K * k)), 1)
            return out
    return img


def shade_corner(canvas, k, rx=0.62, ry=0.55):
    """soft dark falloff from the lower-left corner so thin serif captions read on bright shots."""
    if k <= 0.01: return canvas
    g = np.clip(1.0 - np.hypot(R6.W6["xx"] / (W * rx), (H - R6.W6["yy"]) / (H * ry)), 0, 1) ** 0.9
    return (canvas.astype(np.float32) * (1 - k * g)[..., None]).astype(np.uint8)


def words_line(canvas, ws, offs, t, x0, y, ov=34, f2=1.0):
    x = x0
    for (pm, a), off in zip(ws, offs):
        if t >= off:
            u = clamp((t - off) / 0.15); put(canvas, pm, a, x + a.shape[1] / 2, y + (1 - out_cubic(u)) * 8 * K, opacity=u * f2)
        x += a.shape[1] - ov * K


def hud_brackets(canvas, x0, y0, x1, y1, col, a_=1.0, L=26):
    col = tuple(int(c * a_) for c in col); lw = max(1, int(round(2 * K))); L = int(L * K)
    for (x, y, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x1, y1, -1, -1), (x0, y1, 1, -1)):
        x, y = int(x), int(y); cv2.line(canvas, (x, y), (x + sx * L, y), col, lw, cv2.LINE_AA); cv2.line(canvas, (x, y), (x, y + sy * L), col, lw, cv2.LINE_AA)


def floor_word(canvas, pm, a, t, t0, t1, scale=1.25, y=1.10):
    if not (t0 <= t < t1): return
    dt = t - t0; e = out_expo(dt / 0.16)
    text_plane(canvas, pm, a, Rmat(0, -64, 0), W * 0.5, H * y + (1 - e) * H * 0.3, 0, scale, clamp(dt / 0.05) * clamp((t1 - t) / 0.06))


def lum_through(canvas, under, thr, soft=45.0):
    """light from the footage burns through whatever was drawn on top (words standing inside a beam or fire)."""
    lit = cv2.cvtColor(under, cv2.COLOR_BGR2GRAY).astype(np.float32)
    lm = cv2.GaussianBlur(np.clip((lit - thr) / soft, 0, 1), (0, 0), 3 * K + 0.5)[..., None]
    canvas[:] = (canvas.astype(np.float32) * (1 - lm) + under.astype(np.float32) * lm).astype(np.uint8)


from render2 import text_plane, slam, word_layer, with_shadow


# ======================================================================== INTRO: the identity file
def scene_intro(t, n, acc):
    if t < SH["H1"]["t0"]:                            # static: the signal is still looking for him
        img = render_shot(SH["ST"], t); canvas = cv2.convertScaleAbs(img, alpha=0.55)
        canvas = cut_glitch(canvas, t, (0.21,), 0.12)
    else:
        cur = [s for s in (SH["H1"], SH["H2"], SH["H3"]) if s["t0"] <= t][-1]
        canvas = render_shot(cur, t)
        g = cv2.cvtColor(canvas, cv2.COLOR_BGR2GRAY); canvas = cv2.addWeighted(canvas, 0.78, cv2.merge([g, g, g]), 0.22, 0)      # monitor look
        canvas = (canvas.astype(np.float32) * (1 - 0.10 * X7["scan"][..., None])).astype(np.uint8)
        canvas = cut_glitch(canvas, t, (SH["H1"]["t0"], SH["H2"]["t0"], SH["H3"]["t0"]), 0.10)
    a_ = smooth(t / 0.4)
    R6.frame_lines(canvas, 0.7 * a_, 0.032)
    mx, my = int(W * 0.05), int(H * 0.085)
    if t >= 0.10: pm, a = X7["h_file"]; comp_pm(canvas, pm[:, : int(pm.shape[1] * clamp((t - 0.10) / 0.4))], a[:, : int(a.shape[1] * clamp((t - 0.10) / 0.4))], 0.9, mx, my)
    if int(t * 2.4) % 2 == 0 and t >= 0.21:
        pm, a = X7["h_rec"]; x = W - mx - a.shape[1]; comp_pm(canvas, pm, a, 0.9, x, my); cv2.circle(canvas, (x - int(14 * K), my + a.shape[0] // 2), int(6 * K), (60, 60, 235), -1, cv2.LINE_AA)
    tc = X7["mono"](f"00:00:{int(t):02d}:{int((t % 1) * 24):02d}", 15); comp_pm(canvas, *tc, 0.75, W - mx - tc[1].shape[1], H - my - tc[1].shape[0])
    if 0.30 <= t < 2.55:                              # Misaki's question types itself, letter by letter, as she asks it
        u = clamp((t - 0.30) / 1.30); m = reveal(X7["h_prompt"], u)
        if u >= 1 and int(t * 3) % 2: m = X7["h_prompt"]
        pm, a = layer(m, fill=HUDC, shadow=(5 * K, 0.7, 0, 2 * K)); comp_pm(canvas, pm, a, clamp((2.55 - t) / 0.2), mx, int(H * 0.78))
    s1 = SH["H1"]
    if s1["t0"] <= t < s1["t1"]:                      # scanning the eye
        ex, ey, _ = R4.to_screen(s1, t, ZERO_ACC, 0.60, 0.43); r = 150 * K * (1 + 0.15 * math.sin(t * 9))
        hud_brackets(canvas, ex - r, ey - r * 0.7, ex + r, ey + r * 0.7, HUDC, 0.85)
        pm, a = X7["h_scan"]; comp_pm(canvas, pm, a, 0.85, int(ex - r), int(ey + r * 0.7 + 10 * K))
        pc = X7["mono"](f"{min(99, int((t - s1['t0']) / 1.9 * 100)):02d}%", 15); comp_pm(canvas, *pc, 0.85, int(ex + r - pc[1].shape[1]), int(ey + r * 0.7 + 10 * K))
    s2 = SH["H2"]
    if s2["t0"] <= t < s2["t1"]:
        for (cx, cy) in ((0.27, 0.52), (0.82, 0.46)):
            x, y, _ = R4.to_screen(s2, t, ZERO_ACC, cx, cy); hud_brackets(canvas, x - 150 * K, y - 170 * K, x + 150 * K, y + 170 * K, HUDC, 0.8)
        pm, a = X7["h_body"]; comp_pm(canvas, pm, a, 0.85, int(W * 0.62), int(H * 0.14))
    if t >= 4.54:                                     # the file fills itself in
        x = int(W * 0.60); y = int(H * 0.17)
        pm, a = layer(reveal(X7["h_name"], (t - 4.54) / 0.55), fill=HUDC, shadow=(5 * K, 0.7, 0, 2 * K)); comp_pm(canvas, pm, a, 0.95, x, y)
        if t >= 5.62:
            gl = int(t * 30) % 3 == 0 and t < 5.80; pm, a = X7["h_stat"]; comp_pm(canvas, pm, a, 0.95, x + (int(8 * K) if gl else 0), y + int(40 * K))
        if t >= 5.85:
            pm, a = X7["h_soul"]; comp_pm(canvas, pm, a, 0.95 if int(t * 12) % 2 else 0.4, x, y + int(80 * K))
    # Polka's answer: MARATHON serif, lower left
    w = DW["intro"]
    if 2.40 <= t < 6.15: canvas[:] = shade_corner(canvas, 0.78 * min(clamp((t - 2.40) / 0.25), clamp((6.15 - t) / 0.15)), 0.72, 0.80)
    if 2.45 <= t < 4.05:
        f1 = clamp((4.05 - t) / 0.12)
        words_line(canvas, X7["a1"][:3], [w[6][0], w[7][0], w[8][0]], t, W * 0.05, H * 0.67, ov=40, f2=f1)
        words_line(canvas, X7["a1"][3:], [w[9][0], w[10][0], w[11][0], w[12][0]], t, W * 0.05, H * 0.80, ov=40, f2=f1)
    if t >= 4.05:
        f2 = clamp((6.10 - t) / 0.10)
        words_line(canvas, X7["a2a"], [w[13][0], w[14][0], w[15][0]], t, W * 0.05, H * 0.50, ov=40, f2=f2)
        words_line(canvas, X7["a2b"][:1], [w[16][0]], t, W * 0.05, H * 0.645, ov=0, f2=f2)
        words_line(canvas, X7["a2b"][1:], [w[17][0]], t, W * 0.05, H * 0.805, ov=0, f2=f2)
    return canvas


# ======================================================================== VERSE
def scene_verse(t, n, acc):
    if t < SH["V1"]["t1"]:
        s = SH["V1"]; e = out_expo((t - s["t0"]) / 0.42); img = render_shot(s, t)
        return zoom_at(img, lerp(3.2, 1.0, e), 0.72 * W, 0.18 * H, lerp(0.5, 0.72, e) * W, lerp(0.5, 0.18, e) * H, reflect=True) if e < 0.999 else img
    if t < SH["V2"]["t1"]:
        canvas = fr(SH["V2"], t, acc); slam(canvas, *X7["face3d"], Rmat(-26, 4, 0), W * 0.72, H * 0.50, t, 8.74, lroll=-4); return canvas
    if t < SH["PF"]["t1"]:
        canvas = R4.split_face(t, acc)
        if t >= 9.46:
            u = clamp((t - 9.46) / 0.12); y = H * 0.84
            put(canvas, *X7["face_l"], W * 0.25, y + (1 - out_cubic(u)) * 12 * K, opacity=u); put(canvas, *X7["face_r"], W * 0.75, y + (1 - out_cubic(u)) * 12 * K, opacity=u * 0.85)
        return canvas
    if t < SH["V4"]["t1"]: return R4.ink_cut(SH["V4"], t, acc)
    if t < SH["V5a"]["t1"]: return fr(SH["V5a"], t, acc)
    if t < SH["V5b"]["t1"]:
        s = SH["V5b"]; img, m = render_shot(s, t, acc, want_matte=True); canvas = ink(img, "red", 50)
        dt = t - s["t0"]; e = out_expo(dt / 0.12); pm, a = X7["unmasked"]
        put(canvas, pm, a, W * 0.5, H * 0.50, scale=lerp(1.4, 1.0, e) * (W * 0.94 / a.shape[1]), rot=-8, opacity=clamp(dt / 0.04))
        if m is not None: comp_matte(canvas, ink(img, "wb", 58), m)
        return cut_glitch(canvas, t, (s["t0"],), 0.12)
    if t < SH["V6"]["t1"]:
        canvas = fr(SH["V6"], t, acc)
        if t >= 12.78:
            under = canvas.copy(); dt = t - 12.78; pm, a = X7["armageddon"]
            put(canvas, pm, a, W * 0.56 - dt * 160 * K, H * 0.56, scale=1.0 + 0.04 * dt, opacity=clamp(dt / 0.06)); lum_through(canvas, under, 175.0)
        return canvas
    if t < SH["V7"]["t1"]:                            # v19: the dead children in a floating MARATHON frame; the tears fall out of it
        cur = SH["V7"]; beat = sum(0.012 * math.exp(-(t - b) / 0.07) for b in tl.B if 0 <= t - b < 0.3)
        R, e, u = R2.card_pose(t, cur, (-15, -6), (6, 2), (-2.5, -1.0))
        cw = int(lerp(W * 1.02, W * 0.58, e)) // 2 * 2; ch = cw * 9 // 16 // 2 * 2
        img = render_shot(cur, t, size=(cw, ch)); cx, cy = W * 0.5, lerp(H * 0.5, H * 0.43, e)
        canvas = R2.backdrop(img); R2.plus_markers(canvas, R, t, 4.0, 0.36 * e)
        R2.card(canvas, img, R, cx, cy, 1 + beat, "V7", X7["card_lab"], X7["card_idx"], e)
        if t >= 13.74:
            ls, (tw, th) = X7["L_tears"]; offs = []
            for i in range(len(ls)):
                d = max(0.0, t - 13.95 - i * 0.07); offs.append((0.0, d * d * 1100 * K, clamp((t - 13.74) / 0.15) * clamp(1 - d / 0.34)))
            pm, a = word_layer(X7["L_tears"], YEL, offs, hmul=3.0); pm, a = with_shadow(pm, a, 9 * K, 0.75, 4 * K)
            text_plane(canvas, pm, a, R, cx - cw * 0.20, cy + ch / 2 + a.shape[0] * 0.30, -120, 1.0, 1.0, 1 + beat)
        return canvas
    if t < SH["V8"]["t1"]:
        canvas = fr(SH["V8"], t, acc); floor_word(canvas, *X7["demons"], t, 14.72, 15.21); return canvas
    # V9: the eye turns; on the drop the camera falls through it
    s = SH["V9"]; img = fr(s, t, acc)
    i0 = tl.CHORUS - 0.22
    if t >= i0:
        ex, ey, _ = R4.to_screen(s, t, acc, 0.62, 0.47)
        return iris_through(img, render_shot(SH["D1"], tl.CHORUS + 0.05 + max(0.0, t - tl.CHORUS)), ex, ey, (t - i0) / 0.32, ring=(255, 150, 255))
    return img


# ======================================================================== DROP
TR7 = [(16.85, "whip", "D1", "D2", 0.07, 0.06, (1, 0)), (17.57, "slash", "D2", "D3", 0.06, 0.07, -28), (18.30, "slash", "D3", "D4", 0.06, 0.07, 34),
       (19.01, "fire", "D4", "D5", 0.16, 0.08, (255, 150, 60)), (24.53, "whip", "L1", "L2", 0.07, 0.06, (1, 0)), (25.25, "slash", "L3", "L4", 0.06, 0.07, 24),
       (25.97, "whip", "L4", "L5", 0.07, 0.06, (-1, 0)), (26.70, "fire", "L5", "L6", 0.12, 0.08, (255, 80, 220)),
       (28.36, "whip", "S1", "S2", 0.07, 0.06, (0, -1)), (28.62, "slash", "S2", "S3", 0.06, 0.07, 30), (29.08, "whip", "S3", "S4", 0.07, 0.06, (0, 1))]
WHAT_POS = [(0.80, 0.22, -8), (0.20, 0.28, 6), (0.84, 0.70, -5), (0.22, 0.24, 7), (0.78, 0.26, -6), (0.20, 0.70, 5), (0.82, 0.30, -7), (0.26, 0.66, 6)]


def ring_on_circle(canvas, t):
    s = SH["R1"]; ca = R4.reinc_circle(min(t, SH["R2"]["t0"] + 0.50)); ang = -0.9 * (t - s["t0"]) - 0.4
    if t < SH["R2"]["t0"]: x, y, rr = ca[0], ca[1], ca[2] * 0.64; a_ = clamp((t - s["t0"]) / 0.3)
    else:
        u = (t - SH["R2"]["t0"]) / 0.50; bx, by, bz = R4.to_screen(SH["R2"], t, ZERO_ACC, 0.545, 0.36); cb = (bx, by, 0.05 * W * bz)
        if u < 0.34: x, y, rr = ca[0], ca[1], ca[2] * 0.64
        else:
            e = smooth((u - 0.34) / 0.66); x = lerp(ca[0], cb[0], e); y = lerp(ca[1], cb[1], e); rr = ca[2] * 0.64 * ((cb[2] * 1.6) / (ca[2] * 0.64)) ** e
        a_ = 1.0 - smooth((u - 0.55) / 0.40)
    R6.ring_text(canvas, x, y, rr, ang, a_)


def finale(t, acc):
    s = SH["F6"]; dt = t - s["t0"]
    canvas = render_shot(s, t, acc).copy(); fg, m = render_shot(s, t, acc, want_matte=True, zmul=1.045)
    a_ = smooth((dt - 0.06) / 0.32)
    if a_ > 0.01:
        sc = lerp(0.42, 0.46, clamp(dt / 0.9)); qx, qy = W * 0.5, H * 0.17
        shape = cv2.cvtColor(R4.skull_layer("SKa", SH["SKa"]["t0"] + 0.05, sc, qx, qy), cv2.COLOR_BGR2GRAY)
        shape = cv2.GaussianBlur(shape, (0, 0), 5 * K + 0.5).astype(np.float32) / 255.0
        canvas = np.clip(canvas.astype(np.float32) * ((1.0 - a_) + a_ * (0.34 + 0.86 * shape))[..., None], 0, 255).astype(np.uint8)
        canvas = cv2.add(canvas, cv2.convertScaleAbs(R4.glow_only(R4.skull_layer("SKb", SH["SKb"]["t1"] - 0.01, sc, qx, qy, pal=None), 1.2), alpha=a_))
    if m is not None: comp_matte(canvas, fg, m)
    # the character card: his borrowed name, struck out; his real title beneath
    e = out_expo(dt / 0.16); y = H * 0.76; pm, a = X7["t_name"]
    put(canvas, pm, a, W * 0.5, y + (1 - e) * 20 * K, scale=lerp(1.12, 1.0, e), opacity=clamp(dt / 0.06))
    if t >= 30.95:
        u = out_cubic((t - 30.95) / 0.14); half = a.shape[1] * 0.50; x0 = W * 0.5 - half
        cv2.line(canvas, (int(x0), int(y + 4 * K)), (int(x0 + 2 * half * u), int(y - 2 * K)), VRED, max(3, int(14 * K)), cv2.LINE_AA)
        if t >= 31.05:
            u2 = clamp((t - 31.05) / 0.15); pm, a = X7["t_sub"]; put(canvas, pm, a, W * 0.5, y + 92 * K + (1 - out_cubic(u2)) * 10 * K, opacity=u2)
            pm, a = X7["t_sub2"]; put(canvas, pm, a, W * 0.5, y + 150 * K, opacity=u2 * 0.85)
    return canvas


def scene_drop(t, n, acc):
    tf = R6.trans_frame(t, acc, TR7)
    if 24.74 <= t < 25.09:
        canvas = R6.shatter(fr(SH["L2"], t, acc), fr(SH["L3"], t, acc), (t - 24.74) / 0.35, (0.50, 0.45))
    elif tf is not None: canvas = tf
    elif t < 19.96:
        canvas = fr([s for s in (SH["D1"], SH["D2"], SH["D3"], SH["D4"], SH["D5"]) if s["t0"] <= t][-1], t, acc)
    elif t < 20.40:
        canvas = fr(SH["D6"], t, acc); canvas = cv2.addWeighted(canvas, 1.0, np.full_like(canvas, 255), smooth((t - 20.12) / 0.28), 0)
    elif t < SH["R2"]["t0"]:
        canvas = fr(SH["R1"], t, acc); canvas = cv2.addWeighted(canvas, 1.0, np.full_like(canvas, 255), 1 - smooth((t - 20.40) / 0.35), 0); ring_on_circle(canvas, t)
    elif t < SH["R2"]["t0"] + 0.50:
        ca = R4.reinc_circle(t); bx, by, bz = R4.to_screen(SH["R2"], t, ZERO_ACC, 0.545, 0.36)
        canvas = circle_match(fr(SH["R1"], t), fr(SH["R2"], t), ca, (bx, by, 0.05 * W * bz), (t - SH["R2"]["t0"]) / 0.50); ring_on_circle(canvas, t)
    elif t < 21.95: canvas = fr(SH["R2"], t, acc)
    elif t < 22.27:
        ex, ey, _ = R4.to_screen(SH["R2"], t, acc, 0.545, 0.36); canvas = iris_through(fr(SH["R2"], t, acc), fr(SH["D9"], t), ex, ey, (t - 21.95) / 0.32, ring=(200, 120, 255))
    elif t < SH["D10"]["t0"]: canvas = fr(SH["D9"], t, acc)
    elif t < SH["L1"]["t0"]: canvas = fr(SH["D10"], t, acc)
    elif t < SH["L2"]["t0"]: canvas = R6.glitch_hits(fr(SH["L1"], t, acc), t, SH["L1"]["t0"])
    elif t < SH["F6"]["t0"]:
        canvas = fr([s for s in (SH["L2"], SH["L3"], SH["L4"], SH["L5"], SH["L6"], SH["S1"], SH["S2"], SH["S3"], SH["S4"], SH["S5"]) if s["t0"] <= t][-1], t, acc)
    else: canvas = finale(t, acc)
    if 16.13 <= t < 16.85: slam(canvas, *X7["synthetic"], Rmat(26, -5, 0), W * 0.5, H * 0.52, t, 16.13, lroll=-4)
    for i, wt in enumerate(tl.WHAT):                  # the song's "What?" ad-libs, tagged where they land
        if wt <= t < wt + 0.34:
            x, y, r = WHAT_POS[i % len(WHAT_POS)]; p = pop_in(t, wt, 0.12); put(canvas, *X7["what"], W * x, H * y, scale=p, rot=r, opacity=clamp(p * 2) * clamp((wt + 0.34 - t) / 0.08))
    return canvas


def pop_in(t, t0, d=0.14): return out_back((t - t0) / d) if t >= t0 else 0.0


# ======================================================================== OUTRO
def mirror(t, acc):
    a = render_shot(SH["O1a"], t); b = render_shot(SH["O1b"], t)
    left = zoom_at(a, 1.0, 0.88 * W, 0.48 * H, 0.485 * W, 0.48 * H, reflect=True)
    refl_p = cv2.flip(left, 1)
    sk = zoom_at(b, 2.1, 0.50 * W, 0.40 * H, 0.47 * W, 0.50 * H, reflect=True); refl_s = cv2.flip(sk, 1)
    k = smooth((t - 31.70) / 0.90)
    refl = cv2.addWeighted(refl_p, 1 - k, refl_s, k, 0)
    ripple = (np.sin(np.arange(H, dtype=np.float32) / H * 18 + t * 6) * 3 * K).astype(np.float32)          # the glass is not quite flat
    mx_ = (np.tile(np.arange(W, dtype=np.float32), (H, 1)) + ripple[:, None]); my_ = np.tile(np.arange(H, dtype=np.float32)[:, None], (1, W))
    refl = cv2.remap(refl, mx_, my_, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
    refl = cv2.addWeighted(cv2.convertScaleAbs(refl, alpha=0.78), 1.0, np.full_like(refl, (70, 40, 20)), 0.22, 0)   # cold, darker glass
    canvas = left.copy(); canvas[:, W // 2:] = refl[:, W // 2:]
    sheen = np.clip(1.0 - np.abs(np.arange(W, dtype=np.float32) - W / 2) / (11 * K), 0, 1) ** 1.5
    canvas = cv2.add(canvas, (np.stack([sheen * 120, sheen * 130, sheen * 150], -1)[None, :, :] * np.ones((H, 1, 1), np.float32)).astype(np.uint8))
    if t >= 33.04:
        u = clamp((t - 33.04) / 0.14); y = H * 0.78
        put(canvas, *X7["mir_l"], W * 0.27, y, opacity=u); put(canvas, *X7["mir_r"], W * 0.73, y, opacity=u * 0.75)
    return canvas


def dissolve(img, t, t0, t1):
    if t < t0: return img
    u = clamp((t - t0) / (t1 - t0)); f = R2.A.burn * 0.6 + (W6x() / W) * 0.4
    thr = u * 1.15 - 0.05; gone = np.clip((thr - f) / 0.03, 0, 1)[..., None]; edge = np.clip(1 - np.abs(f - thr) / 0.035, 0, 1) ** 2
    out = img.astype(np.float32) * (1 - gone) + np.stack([edge * 255, edge * 235, edge * 150], -1)
    rng = np.random.default_rng(int(t * 60))
    ys, xs = np.where(edge[::6, ::6] > 0.5)
    for j in rng.choice(len(ys), size=min(len(ys), 160), replace=False) if len(ys) else []:
        y, x = ys[j] * 6, xs[j] * 6; dy = int(rng.random() * 60 * K)
        cv2.circle(out, (int(x + rng.normal(0, 8 * K)), int(y - dy)), max(1, int(2 * K)), (255, 240, 200), -1, cv2.LINE_AA)
    return np.clip(out, 0, 255).astype(np.uint8)


def W6x():
    return R6.W6["xx"]


def scene_outro(t, n, acc):
    if t < SH["O1a"]["t1"]: return mirror(t, acc)
    if t < SH["O2"]["t1"]:
        canvas = shade_corner(fr(SH["O2"], t, acc), 0.88 * clamp((t - 34.30) / 0.2), 0.75, 0.85); R6.frame_lines(canvas, 0.6, 0.06)
        if t >= 34.46:
            pm, a = X7["h_mis"]; comp_pm(canvas, pm, a, 0.95 if int(t * 6) % 2 else 0.35, int(W * 0.08), int(H * 0.17))
            words_line(canvas, [X7["recog"]], [34.46], t, W * 0.08, H * 0.62); words_line(canvas, [X7["myself"]], [34.88], t, W * 0.08, H * 0.74)
        return cut_glitch(canvas, t, (34.46,), 0.10)
    if t < SH["O3"]["t1"]:
        canvas = dissolve(fr(SH["O3"], t, acc), t, 36.10, 37.20)
        if t >= 36.52:
            ls, (tw, th) = X7["L_dis"]; offs = []
            for i in range(len(ls)):
                d = max(0.0, t - 36.75 - i * 0.03); offs.append(((i - len(ls) / 2) * d * 60 * K + tw * 0.25, -d * 140 * K, clamp((t - 36.52) / 0.15) * clamp(1 - d / 0.5)))
            pm, a = word_layer(X7["L_dis"], CREAM, offs, wmul=1.5, hmul=1.8); pm, a = with_shadow(pm, a, 8 * K, 0.7, 3 * K); put(canvas, pm, a, W * 0.5, H * 0.70)
        return canvas
    if t < SH["O4"]["t1"]:
        canvas = fr(SH["O4"], t, acc)
        if t >= 37.88:                                # the word sits behind the hooded figure
            under = canvas.copy(); dt = t - 37.88; pm, a = X7["mask"]
            put(canvas, pm, a, W * 0.56, H * 0.52, scale=1.0 + 0.03 * dt, opacity=clamp(dt / 0.10) * 0.92)
            g = cv2.cvtColor(under, cv2.COLOR_BGR2GRAY).astype(np.float32); fig = cv2.GaussianBlur(np.clip((140.0 - g) / 40.0, 0, 1), (0, 0), 2 * K + 0.5)[..., None]
            canvas[:] = (canvas.astype(np.float32) * (1 - fig) + under.astype(np.float32) * fig).astype(np.uint8)
        return canvas
    canvas = fr(SH["O5"], t, acc); canvas = cv2.convertScaleAbs(canvas, alpha=1.0 - 0.80 * smooth((t - 40.10) / 0.60))
    if t >= 40.06: put(canvas, *X7["nothing"], W * 0.5, H * 0.74, opacity=clamp((t - 40.06) / 0.15) * clamp((40.78 - t) / 0.15))
    return canvas


# ======================================================================== TAG + END CARD
def scene_tag(t, n, acc):
    s = SH["T1"]; canvas = render_shot(s, t, acc)
    canvas = cv2.convertScaleAbs(canvas, alpha=lerp(0.30, 1.0, smooth((t - 40.80) / 0.8)))
    k = smooth((t - 44.40) / 0.45)                    # "...not on the inside": the skull shows through his face
    if k > 0.01:
        z, cx, cy = R4.cam(s, t, ZERO_ACC); ey = ((0.405 - cy) * z + 0.5) * H; d = 0.27 * z
        sk = R4.skull_layer("SKb", SH["SKb"]["t1"] - 0.01, d, W * 0.5, ey)
        canvas = cv2.addWeighted(canvas, 1.0 - 0.55 * k, sk, 0.75 * k, 0)
        canvas = cv2.add(canvas, cv2.convertScaleAbs(R4.glow_only(R4.skull_layer("SKb", SH["SKb"]["t1"] - 0.01, d, W * 0.5, ey, pal=None), 1.3), alpha=k))
    return cv2.convertScaleAbs(canvas, alpha=clamp((45.15 - t) / 0.12))


def tag_captions(canvas, t):
    wd = {i: x for i, x in enumerate(DW["tag"])}; ws = [x[0] for x in DW["tag"]]
    ws[0] = 40.84
    bar = tl.letterbox(t) * H; yA, yB = H - bar - 84 * K, H - bar / 2 - 4 * K
    L = X7["tag"]
    if t < 41.92: words_line(canvas, L[0], ws[0:3], t, W * 0.05, yB, f2=clamp((41.92 - t) / 0.1))
    elif t < 43.90:
        f2 = clamp((43.90 - t) / 0.1); words_line(canvas, L[1], ws[3:7], t, W * 0.05, yA, f2=f2); words_line(canvas, L[2], [ws[7], ws[8]], t, W * 0.05, yB, f2=f2)
    elif t < 45.15:
        f2 = clamp((45.15 - t) / 0.1); words_line(canvas, L[3], ws[9:12], t, W * 0.05, yA, f2=f2); words_line(canvas, L[4], ws[12:15], t, W * 0.05, yB, f2=f2)


def scene_card(t, n):
    s = SH["G2"]; frs = CLIPS.get(s); dt = t - s["t0"]
    src = lerp(1297.46, 1297.25, clamp(dt / 0.14)) if dt < 0.14 else 1296.55 - 0.08 * dt
    fi = max(0, min(len(frs) - 1, int(round((src - s["ss"]) * tl.SRC_FPS))))
    img = frs[fi] if frs[fi].shape[1] == W else cv2.resize(frs[fi], (W, H))
    canvas = np.full((H, W, 3), 246, np.uint8) if dt >= 0.14 else img.copy()
    if dt >= 0.14:
        logo = zoom_at(img, 0.80 * (1 + 0.012 * dt), W * 0.5, H * 0.5, W * 0.5, H * 0.43); m = np.zeros((H, W), np.uint8)
        x0, y0 = int(W * 0.1), int(H * 0.43 - H * 0.40); m[y0:y0 + int(H * 0.80), x0:x0 + int(W * 0.80)] = 255; comp_matte(canvas, logo, m)
        u = clamp((dt - 0.55) / 0.35)
        if u > 0:
            put(canvas, *X7["b1"], W * 0.5, H * 0.875, opacity=u); put(canvas, *X7["b2"], W * 0.5, H * 0.925, opacity=u)
            put(canvas, *X7["b3"], W * 0.5 + X7["b1"][1].shape[1] / 2 + 62 * K, H * 0.873, opacity=u)
    return cv2.convertScaleAbs(canvas, alpha=clamp((tl.END - t) / 0.35))


# ======================================================================== post + dispatch
def accents7(t):
    a = dict(zoom=0.0, shake=0.0, rgb=0.0, glow=0.0, flash=0.0)
    for s in tl.SHOTS:
        p = s["punch"]
        if p <= 0: continue
        dt = t - s["t0"]
        if 0 <= dt < 0.6:
            a["zoom"] += 0.085 * p * math.exp(-dt / 0.085); a["shake"] += 15.0 * p * math.exp(-dt / 0.13)
            a["rgb"] += 3.2 * p * math.exp(-dt / 0.14); a["glow"] += 0.55 * p * math.exp(-dt / 0.16); a["flash"] += 0.16 * p * math.exp(-dt / 0.05)
    if 8.03 <= t < tl.DROP_END:
        for b in tl.B:
            dt = t - b
            if 0 <= dt < 0.3: a["zoom"] += 0.012 * math.exp(-dt / 0.07)
    return a


def inked7(t):
    act = [s for s in tl.SHOTS if s["t0"] <= t < s["t1"] and s["mode"] not in ("split",)]
    return bool(act) and bool(act[-1].get("ink"))


def groove7(canvas, t):
    if not (tl.CHORUS <= t < tl.DROP_END): return canvas
    dx = dy = rot = 0.0
    for i, b in enumerate(tl.B):
        dt = t - b
        if 0 <= dt < 0.28:
            e = math.exp(-dt / 0.065) * math.sin(min(dt / 0.05, 1.0) * math.pi / 2)
            if i % 2 == 0: dy += 11 * K * e
            else: dx += (9 if i % 4 == 1 else -9) * K * e
            rot += (0.55 if i % 4 < 2 else -0.55) * e
    if abs(dx) + abs(dy) + abs(rot) < 0.05: return canvas
    M = cv2.getRotationMatrix2D((W / 2, H / 2), rot, 1.0 + (abs(dx) + abs(dy)) / W * 2.2); M[0, 2] += dx; M[1, 2] += dy
    return cv2.warpAffine(canvas, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)


def post7(img, t, acc, n, grain=0.085, glow0=0.10, vig=1.0, ca=True, streak=True, hal=True):
    A = R2.A; ga = glow0 + acc["glow"]
    sm = cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    bl = cv2.GaussianBlur(cv2.subtract(sm, np.full_like(sm, 140)), (0, 0), W / 4 * 0.022)
    img = cv2.addWeighted(img, 1.0, cv2.resize(bl, (W, H), interpolation=cv2.INTER_LINEAR), ga * 2.2, 0)
    if streak:
        st = cv2.blur(cv2.subtract(sm, np.full_like(sm, 185)), (int(W / 4 * 0.42) | 1, 1)); st = cv2.multiply(st, np.full_like(st, (255, 170, 120)), scale=1 / 255.0)
        img = cv2.addWeighted(img, 1.0, cv2.resize(st, (W, H), interpolation=cv2.INTER_LINEAR), 1.5, 0)
    e = (0.7 + acc["rgb"]) * 0.0011
    if e > 0.0004 and ca:
        b, g, r = cv2.split(img)
        r = cv2.warpAffine(r, np.float32([[1 + e, 0, -e * W / 2], [0, 1 + e, -e * H / 2]]), (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
        b = cv2.warpAffine(b, np.float32([[1 - e, 0, e * W / 2], [0, 1 - e, e * H / 2]]), (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
        img = cv2.merge([b, g, r])
    fl = acc["flash"]
    for f0, fd, fa in tl.FLASHES:
        if f0 <= t < f0 + fd: fl += fa * (1 - (t - f0) / fd)
    if fl > 0.004: img = cv2.addWeighted(img, 1.0, np.full_like(img, 255), min(fl, 1.0), 0)
    if hal:
        lum = cv2.cvtColor(cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY).astype(np.float32)
        hl = np.clip((lum - 218.0) / 37.0, 0, 1); hl = np.clip(cv2.GaussianBlur(hl, (0, 0), W / 4 * 0.010) - cv2.GaussianBlur(hl, (0, 0), W / 4 * 0.002) * 0.6, 0, 1)
        img = cv2.add(img, cv2.resize(np.stack([hl * 16, hl * 40, hl * 105], -1).astype(np.float32), (W, H)).astype(np.uint8))
    img = cv2.addWeighted(img, 1.0, A.noise[(n // max(1, FPS // 24)) % 6], grain, -128 * grain)
    if vig > 0.001: img = cv2.multiply(img, A.vig if vig >= 0.999 else cv2.addWeighted(A.vig, vig, np.full_like(A.vig, 255), 1 - vig, 0), scale=1 / 255.0)
    return img


_LIFT = None


def shadow_lift7(canvas, t):
    global _LIFT
    if not (8.03 <= t < tl.SONG_END): return canvas
    sm = cv2.resize(canvas, (64, 36), interpolation=cv2.INTER_AREA); lo = (cv2.cvtColor(sm, cv2.COLOR_BGR2GRAY) < 26).mean(); k = clamp((lo - 0.30) / 0.30)
    if k <= 0.01: return canvas
    if _LIFT is None:
        x = np.arange(256, dtype=np.float32) / 255.0; _LIFT = np.clip(255 * (x + 0.10 * (1 - x) ** 3.2), 0, 255).astype(np.uint8).reshape(256, 1)
    return cv2.addWeighted(canvas, 1 - 0.75 * k, cv2.LUT(canvas, cv2.merge([_LIFT] * 3)), 0.75 * k, 0)


SIG_HIDE = [(0.0, 8.03), (tl.SONG_END + 0.15, tl.END)]


def signature(canvas, t):
    a_ = 1.0
    for a, b in SIG_HIDE:
        if a - 0.2 <= t < b + 0.2: a_ = min(a_, max(clamp((a - t) / 0.2), clamp((t - b) / 0.2)))
    if a_ <= 0.01: return
    pm, a = X7["sig"]; put(canvas, pm, a, W * 0.035 + a.shape[1] / 2, H * 0.915, opacity=0.30 * a_)


def frame_at(n):
    t = n / FPS; acc = accents7(t); kw = dict(grain=0.085, glow0=0.10, vig=1.0, ca=True, streak=True, hal=True)
    if t < tl.LOGO_T[0]: canvas = scene_intro(t, n, acc); acc = ZERO_ACC; kw.update(streak=False, hal=False, grain=0.10)
    elif t < tl.LOGO_T[4]: canvas = R2.scene_logo(t, n); acc = ZERO_ACC; kw.update(glow0=0.0, vig=0.0, ca=False, grain=0.05, streak=False, hal=False)
    elif t < tl.CHORUS + 0.10: canvas = scene_verse(t, n, acc); kw.update(streak=False)
    elif t < tl.DROP_END: canvas = scene_drop(t, n, acc)
    elif t < tl.TAG_T: canvas = scene_outro(t, n, acc); kw.update(streak=False)
    elif t < tl.CARD_T: canvas = scene_tag(t, n, acc); kw.update(streak=False, hal=False)
    else: canvas = scene_card(t, n); acc = ZERO_ACC; kw.update(glow0=0.0, vig=0.0, ca=False, grain=0.04, streak=False, hal=False)
    if 8.03 <= t < tl.DROP_END and inked7(t): kw.update(glow0=0.03, streak=False, vig=0.55, hal=False)
    canvas = post7(canvas, t, acc, n, **kw)
    canvas = shadow_lift7(groove7(canvas, t), t)
    bar = int(round(tl.letterbox(t) * H))
    if bar > 0: canvas[:bar] = 0; canvas[H - bar:] = 0
    if tl.TAG_T <= t < tl.CARD_T: tag_captions(canvas, t)
    signature(canvas, t)
    return canvas


def worker(args):
    wi, n0, n1 = args; setup()
    out = f"{ROOT}/out/{MODE}7_part{wi}.mp4"
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
    with open(f"{ROOT}/out/{MODE}7_parts.txt", "w") as f:
        for p in parts: f.write(f"file '{p}'\n")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{ROOT}/out/{MODE}7_parts.txt", "-c", "copy", f"{ROOT}/out/{MODE}7_video.mp4"], check=True)
    print("wrote", f"{ROOT}/out/{MODE}7_video.mp4", n1 - n0, "frames")
