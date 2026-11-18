"""V5 renderer = V3 (official logos, cafe fight, colour) with every piece of on-screen type redone in the reference edits' fonts.
usage: render5.py [draft|final] [t_start t_end] -> out/<mode>5_video.mp4
  thin serif caps (Newsreader 200)      <- the MARATHON reference: stacks on the frame edge, dialogue
  heavy oblique grotesque (Archivo 900) <- the JPOXI reference: one word at a time, 3D, glow, colour from the scene
  skewed heavy caps (Anton)             <- the VRENS reference: white stack with one red line
  bold italic Didone (Playfair 900)     <- the VRENS title cards"""
import subprocess, multiprocessing as mp
from r2core import *
import render2 as R2
from render2 import (word_layer, with_shadow, full, backdrop, plus_markers, card, text_plane, pop_in, card_pose, slam, PH,
                     end_logo_frame, SH, OPEN, MID, CLOSE)

SERIF = ("Newsreader.ttf", (200, 72)); SERIF_D = ("Newsreader.ttf", (300, 72)); SERIF_F = ("Newsreader.ttf", (380, 72))
HEAVY = ("ArchivoItalic.ttf", (900, 75)); DIDONE = ("PlayfairItalic.ttf", 900)
YEL = (74, 238, 228); CREAM = (214, 236, 246); VRED = (34, 28, 240); DARK = (26, 20, 24)
PITCH = 150                      # line pitch of the serif stacks (px at 1080p)
T = {}


# ---------------------------------------------------------------- type builders
def serif(text, size, col=YEL, face=SERIF, vcrop=False, tracking=-2.0):
    m = tmask(text, face[0], size * K, tracking=tracking * K, wght=face[1], vcrop=vcrop)
    return layer(m, fill=col, shadow=(9 * K, 0.75, 0, 4 * K))


JP = {"hot": dict(grad=((70, 170, 255), (28, 40, 235)), ex=(16, 8, 70), glow=((40, 110, 255), 0.55)),
      "bone": dict(fill=CREAM, ex=(30, 26, 34), glow=(CREAM, 0.40)),
      "cold": dict(fill=(214, 240, 150), ex=(60, 50, 8), glow=((200, 220, 80), 0.55))}


def jword(text, size, style="hot"):
    st = JP[style]; m = tmask(text, HEAVY[0], size * K, tracking=-3 * K, wght=HEAVY[1])
    n = max(3, int(round(7 * K)))
    return layer(m, fill=st.get("fill", CREAM), grad=st.get("grad"), extrude=(n, 1.0, 1.0, st["ex"]), glow=(st["glow"][0], 16 * K, st["glow"][1]))


def shear(mask, k=0.20):
    h, w = mask.shape; return cv2.warpAffine(mask, np.float32([[1, -k, k * h], [0, 1, 0]]), (w + int(k * h) + 2, h))


def vline(text, size, col=(250, 250, 250)):
    m = shear(tmask(text, "Anton.ttf", size * K, tracking=1 * K))
    return layer(m, fill=col, extrude=(max(3, int(round(8 * K))), 1.0, 1.0, (8, 6, 8)))


def setup():
    cv2.setNumThreads(1); R2.A = R2.Assets(); A = R2.A; k = K
    A.names = [np.zeros((8, 8), np.uint8)] * 4                                   # no handwriting on the photos
    T["ink"] = {w: tmask(w, SERIF_F[0], sz * k, wght=SERIF_F[1], vcrop=False, tracking=-1 * k)
                for w, sz in (("ALL", 84), ("I", 84), ("WANTED", 84), ("WAS", 72), ("PEACE.", 130), ("NOTHING", 72), ("MORE.", 72))}
    T["stack"] = {w: serif(w, 200, YEL, SERIF_D) for w in ("MOUNTAIN", "HIGH", "VALLEY", "LOW", "RIVER")}
    T["L_wide"] = letters("WIDE", SERIF_D[0], 200 * k, tracking=-2 * k, wght=SERIF_D[1])
    T["L_far"] = letters("FAR", SERIF_D[0], 230 * k, tracking=-2 * k, wght=SERIF_D[1])
    T["enough_v"] = jword("ENOUGH", 300, "hot"); T["call"] = jword("CALL", 260, "hot"); T["where"] = jword("WHERE", 220, "cold")
    T["hurry"] = jword("HURRY", 260, "hot"); T["worry"] = jword("WORRY", 230, "bone")
    T["c_aint"] = jword("AIN’T", 400, "hot"); T["c_no"] = [jword(c, 560, "bone") for c in "NO"]
    T["c_mount"] = jword("MOUNTAIN", 300, "hot"); T["c_high"] = jword("HIGH", 470, "hot")
    T["c_en"] = [jword("ENO", 330, "hot"), jword("UGH", 330, "hot")]
    T["shinjuku"] = serif("SHINJUKU", 170, YEL, SERIF_D); T["loc"] = A.mono("TOKYO   ·   PRESENT DAY", 16)
    T["names"] = [vline("THE KIDS", 70), vline("MISAKI", 92), vline("TAKUMI", 110), vline("ME", 150, VRED)]
    T["d_prot"] = [serif(w, 104, CREAM, SERIF_D) for w in ("I’LL", "PROTECT", "YOU,")]
    T["d_nmw"] = [layer(tmask(w, DIDONE[0], 132 * k, wght=DIDONE[1], vcrop=False), fill=VRED, shadow=(9 * k, 0.6, 0, 4 * k)) for w in ("NO", "MATTER", "WHAT.")]
    T["d_close"] = [serif(w, 58, YEL, SERIF_D) for w in ("IT", "SEEMS", "THIS", "LAND", "I’VE", "ARRIVED", "IN", "IS")]
    T["peaceful"] = layer(tmask("PEACEFUL.", SERIF_D[0], 200 * k, tracking=-2 * k, wght=SERIF_D[1]), fill=DARK, glow=(CREAM, 10 * k, 0.55))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    T["corner"] = np.clip(1.0 - np.hypot(xx / W / 0.62, (H - yy) / H / 0.80), 0, 1) ** 1.1


# ---------------------------------------------------------------- A. film reel: dialogue as thin serif caps
def film_text(pic, t):
    A = R2.A; pw, ph = A.pw, A.ph; I = T["ink"]
    def ink_(mask, x_left, cy, t0, op=0.92):
        if t < t0: return
        u = clamp((t - t0) / 0.30); m = mask
        if u < 1: m = cv2.GaussianBlur(mask, (0, 0), (1 - u) * 5 * K + 0.1)
        pm, a = layer(m, fill=DARK); comp_pm(pic, pm, a, op * smooth(u * 1.6), int(x_left), int(cy - a.shape[0] / 2))
    if t < 2.02:                                     # a two-line stack, left of the child
        x = pw * 0.075
        for w, off in (("ALL", 0.0), ("I", 0.20)): ink_(I[w], x, ph * 0.40, OPEN + off); x += I[w].shape[1] + 22 * K
        ink_(I["WANTED"], pw * 0.075, ph * 0.515, OPEN + 0.36)
    elif t < 3.92:
        ink_(I["WAS"], pw * 0.565, ph * 0.10, OPEN + 1.95); ink_(I["PEACE."], pw * 0.565, ph * 0.215, OPEN + 2.17)
    else:
        x = pw * 0.60
        for w, off in (("NOTHING", 0.0), ("MORE.", 0.30)): ink_(I[w], x, ph * 0.60, OPEN + 3.60 + off); x += I[w].shape[1] + 20 * K


# ---------------------------------------------------------------- C. verse
def dim_bottom(img, k=0.62):
    h = img.shape[0]; g = 1.0 - k * np.clip((np.arange(h, dtype=np.float32) / h - 0.50) / 0.50, 0, 1) ** 1.2
    return (img.astype(np.float32) * g[:, None, None]).astype(np.uint8)


def stack2(canvas, R, cx, cy, l1, t1, l2, t2, t, cam, l2_layer=None):
    """two tight lines of thin serif caps sitting on the frame's lower edge."""
    if t >= t1:
        u = clamp((t - t1) / 0.12); pm, a = T["stack"][l1]
        text_plane(canvas, pm, a, R, cx, cy + (1 - out_cubic(u)) * 14 * K, -120, 1.0, u, cam)
    if t >= t2:
        u = clamp((t - t2) / 0.12); pm, a = l2_layer or T["stack"][l2]
        text_plane(canvas, pm, a, R, cx, cy + PITCH * K + (1 - out_cubic(u)) * 14 * K, -120, 1.0, u, cam)


def scene_verse(t, n, acc):
    A = R2.A
    cur = [s for s in tl.SHOTS if s["name"].startswith("C") and s["t0"] <= t < s["t1"]][-1]; nm = cur["name"]
    beat = sum(0.012 * math.exp(-(t - b) / 0.07) for b in tl.B if 0 <= t - b < 0.3)
    if nm == "C2":
        R, e, u = card_pose(t, cur, (-17, -7), (5, 2), (-2.5, -1.0))
        cw = int(lerp(W * 1.02, W * 0.56, e)) // 2 * 2; ch = cw * 9 // 16 // 2 * 2
        img = render_shot(cur, t, size=(cw, ch)); cx, cy = W * 0.5, lerp(H * 0.5, H * 0.43, e)
        canvas = backdrop(img); plus_markers(canvas, R, t, 1.0, 0.36 * e)
        card(canvas, dim_bottom(img), R, cx, cy, 1 + beat, "C2", A.card_labels["C2"], A.card_idx["C2"], e)
        stack2(canvas, R, cx - cw * 0.15, cy + ch / 2 - 0.22 * PITCH * K, "MOUNTAIN", 9.10, "HIGH", 9.58, t, 1 + beat)
        return canvas
    if nm == "C4":
        R, e, u = card_pose(t, cur, (7, 2), (26, 15), (1.5, 0.5))
        cw = int(lerp(W * 1.02, W * 0.54, e)) // 2 * 2; ch = cw * 9 // 16 // 2 * 2
        img = render_shot(cur, t, size=(cw, ch)); cx, cy = W * 0.5, lerp(H * 0.5, H * 0.40, e)
        canvas = backdrop(img); plus_markers(canvas, R, t, 2.0, 0.36 * e)
        card(canvas, dim_bottom(img), R, cx, cy, 1 + beat, "C4", A.card_labels["C4"], A.card_idx["C4"], e)
        stack2(canvas, R, cx - cw * 0.15, cy + ch / 2 - 0.22 * PITCH * K, "VALLEY", 10.96, "LOW", 11.50, t, 1 + beat)
        return canvas
    if nm in ("C6a", "C6b"):
        s0 = SH["C6a"]; t0 = s0["t0"]; t1 = SH["C6b"]["t1"]; uu = clamp((t - t0) / (t1 - t0)); e = out_expo((t - t0) / 0.20)
        wd = smooth((t - 13.26) / 0.30)
        R = Rmat(lerp(15, -11, smooth(uu)) * e + slow(t, 4.0), -3 * e, 1.5 * e)
        asp = lerp(16 / 9, 2.9, wd); cw = int(lerp(W * 1.02, W * lerp(0.56, 0.80, wd), e)) // 2 * 2; ch = int(cw / asp) // 2 * 2
        img = render_shot(cur, t, size=(cw, ch)); cx, cy = W * lerp(0.47, 0.53, uu), lerp(H * 0.5, H * 0.43, e)
        canvas = backdrop(img); plus_markers(canvas, R, t, 3.0, 0.36 * e)
        card(canvas, dim_bottom(img), R, cx, cy, 1 + beat, "C6", A.card_labels["C6"], A.card_idx["C6"], e)
        ls, (tw, th) = T["L_wide"]; sp = wd * 120 * K                              # the letters of the second line drift apart
        pm, a = word_layer(T["L_wide"], YEL, [((i - 1.5) * sp + tw * 0.4, 0.0, 1.0) for i in range(len(ls))], wmul=1.8)
        pm, a = with_shadow(pm, a, 9 * K, 0.75, 4 * K)
        stack2(canvas, R, cx - cw * 0.12, cy + ch / 2 - 0.22 * PITCH * K, "RIVER", 12.59, "WIDE", 13.26, t, 1 + beat, l2_layer=(pm, a))
        return canvas
    canvas = full(t, acc)
    if 14.08 <= t < 14.86: slam(canvas, *T["enough_v"], Rmat(-26, 4, 0), W * 0.52, H * 0.64, t, 14.08, lroll=-4)
    return canvas


# ---------------------------------------------------------------- D. Shinjuku + the two worlds
def scene_d(t, n, acc):
    A = R2.A
    if 19.50 <= t < 21.34: return scene_duo(t, n, acc)
    canvas = full(t, acc)
    if 17.28 <= t < 17.65: slam(canvas, *T["call"], Rmat(24, -4, 0), W * 0.70, H * 0.64, t, 17.28, lroll=-5)
    if 17.65 <= t < 19.70:                           # location card in the frame-edge serif
        dt = t - 17.65; fo = clamp((19.70 - t) / 0.18)
        g = np.clip(1.0 - np.arange(W, dtype=np.float32) / (W * 0.46), 0, 1) ** 1.3 * 0.66 * fo * clamp(dt / 0.25)
        canvas[:] = (canvas.astype(np.float32) * (1 - g)[None, :, None]).astype(np.uint8)
        pm, a = T["shinjuku"]; u = clamp(dt / 0.16); y0 = H * 0.585
        comp_pm(canvas, pm, a, fo * u, int(W * 0.04), int(y0 + (1 - out_cubic(u)) * 14 * K))
        y2 = int(y0 + a.shape[0] * 0.80)
        if dt > 0.2:
            comp_pm(canvas, *T["loc"], 0.9 * fo * clamp((dt - 0.2) / 0.2), int(W * 0.052), y2)
            comp_pm(canvas, *A.loc_co, 0.8 * fo * clamp((dt - 0.35) / 0.2), int(W * 0.052), y2 + int(30 * K))
    if 18.55 <= t < 19.50: slam(canvas, *T["where"], Rmat(-28, 3, 0), W * 0.71, H * 0.60, t, 18.55, lroll=4)
    return canvas


def scene_duo(t, n, acc=ZERO_ACC):
    A = R2.A
    u = clamp((t - 19.50) / 1.84); e = out_expo((t - 19.50) / 0.30); far = smooth((t - 19.75) / 1.55)
    R = Rmat(lerp(0, -9, far) + slow(t, 5), 2 * slow(t, 6), 0)
    cw = int(W * 0.44) // 2 * 2; ch = cw * 9 // 16 // 2 * 2
    il = render_shot(SH["D5L"], t, size=(cw, ch)); ir = render_shot(SH["D5R"], t, size=(cw, ch))
    canvas = cv2.addWeighted(backdrop(il, 0.16), 1.0, backdrop(ir, 0.14), 1.0, 0)
    canvas[:] = cv2.convertScaleAbs(canvas, alpha=e)
    if e < 0.995 and t < SH["D4"]["t1"]: canvas[:] = cv2.addWeighted(canvas, 1.0, full(t, acc), 1 - e, 0)
    plus_markers(canvas, R, t, 5.0, 0.36 * e)
    lx, ly, lz = lerp(W * 0.27, W * 0.16, far), lerp(H * 0.5, H * 0.30, far) + (1 - e) * H, lerp(0, 1900 * K, far)
    rx, ry, rz = lerp(W * 0.73, W * 0.70, far), lerp(H * 0.5, H * 0.56, far) - (1 - e) * H, lerp(0, -300 * K, far)
    Rl = Rmat(lerp(0, 30, far), 0, lerp(0, -3, far)); f = 1.7 * W
    def scr(x, y, z, Rm):
        p = np.array([x - W / 2, y - H / 2, z]) @ Rm.T; return np.array([W / 2 + f * p[0] / (f + p[2]), H / 2 + f * p[1] / (f + p[2])])
    pa, pb = np.array([lx, ly]), scr(rx, ry, rz, R)
    if far > 0.05:
        nseg = 26; col = tuple(int(c * 0.7 * far) for c in BONE)
        for i in range(0, nseg, 2):
            a_, b_ = pa + (pb - pa) * i / nseg, pa + (pb - pa) * (i + 1) / nseg
            cv2.line(canvas, (int(a_[0]), int(a_[1])), (int(b_[0]), int(b_[1])), col, max(1, int(1.5 * K)), cv2.LINE_AA)
    ql = quad3d(cw, ch, lx, ly, lz, None, Rl=Rl, screen=True); im = il.copy(); cv2.rectangle(im, (0, 0), (cw - 1, ch - 1), BONE, max(1, int(3 * K)))
    draw_plane(canvas, cv2.convertScaleAbs(im, alpha=lerp(1.0, 0.72, far)), np.full((ch, cw), 255, np.uint8), ql)
    card(canvas, ir, R, rx, ry, 1.0, "D5R", None, None, e * 0.9)
    for mn, q in ((A.lab_other[1], ql), (A.lab_shin[1], quad3d(cw, ch, rx, ry, rz, R))):
        comp_pm(canvas, *mn, 0.85 * e, int(q[3][0]), int(q[3][1] + 14 * K))
    if far > 0.3:
        mid = (pa + pb) / 2; pm, a = A.apart; ang = -math.degrees(math.atan2(pb[1] - pa[1], pb[0] - pa[0]))
        put(canvas, pm, a, mid[0], mid[1] - 16 * K, rot=-ang, opacity=clamp((far - 0.3) / 0.2) * 0.9)
    if t >= 20.42:                                   # the letters drift apart like the two worlds
        ls, (tw, th) = T["L_far"]; spread = smooth((t - 20.60) / 0.7) * 100 * K; offs = []
        for i in range(len(ls)):
            ui = (t - 20.42 - i * 0.04) / 0.16
            offs.append(((i - 1) * spread + tw * 0.5, (1 - out_back(ui)) * th * 0.3 if ui > 0 else th, clamp(ui * 3)))
        pm, a = word_layer(T["L_far"], YEL, offs, wmul=2.0); pm, a = with_shadow(pm, a, 9 * K, 0.75, 4 * K)
        put(canvas, pm, a, W * 0.44, H * 0.79)
    return canvas


# ---------------------------------------------------------------- E. polaroids + the names as a skewed stack
def scene_polaroid(t, n):
    A = R2.A
    canvas = A.table.copy()
    zt = smooth((t - 25.54) / 0.26); drift = (t - 22.04) / 3.5
    p4 = PH[3]; icy_off = -(A.pbb - A.pb) / 2 * p4["sc"]
    for i, p in enumerate(PH):
        s = SH[p["name"]]
        if t < s["t0"]: continue
        dt = t - s["t0"]; e = out_expo(dt / 0.22); sgn = 1 if i % 2 == 0 else -1
        pm, a = R2.photo_tex(p, t)
        sc = p["sc"] * lerp(1.55, 1.0, e) * (1 + 0.04 * drift); rot = p["rot"] + sgn * 13 * (1 - e) + 0.8 * slow(t, i + 1.0)
        cx = W * p["pos"][0] + (W * 0.5 - W * p["pos"][0]) * -0.04 * drift; cy = H * p["pos"][1] - (1 - e) * H * 0.10
        cy += -A.ptop / 2 * sc
        if zt > 0:
            tx, ty = W * p4["pos"][0], H * p4["pos"][1] + icy_off
            zs = lerp(1.0, (W / (A.iw * p4["sc"])) * 1.02, in_expo(zt) * 0.5 + zt * 0.5)
            cx = W / 2 + (cx - tx) * zs + (tx - W / 2) * (1 - zt); cy = H / 2 + (cy - ty) * zs + (ty - H / 2) * (1 - zt)
            sc *= zs; rot = lerp(rot, rot - p4["rot"], zt)
        op = clamp(dt / 0.05); shs = A.pshadow; so = lerp(26, 14, e) * K
        put(canvas, np.zeros((shs.shape[0], shs.shape[1], 3), np.uint8), shs, cx + so * 0.6, cy + A.ptop / 2 * sc + so, scale=sc, rot=rot, opacity=0.55 * op)
        put(canvas, pm, a, cx, cy, scale=sc, rot=rot, opacity=op)
    fo = 1 - zt
    if fo > 0.01:                                    # name stack: white lines, the last one red
        th_ = math.radians(-7); ct, st = math.cos(th_), math.sin(th_); ox, oy = W * 0.04, H * 0.575; y = 0.0; Rv = Rmat(16, 0, 0)
        for i, (pm, a) in enumerate(T["names"]):
            t0 = SH[PH[i]["name"]]["t0"] + 0.10; hgt = a.shape[0]
            if t >= t0:
                e = out_expo((t - t0) / 0.12); lx_, ly_ = a.shape[1] / 2, y + hgt / 2
                text_plane(canvas, pm, a, Rv, ox + lx_ * ct - ly_ * st, oy + lx_ * st + ly_ * ct, -40, lerp(1.6, 1.0, e), clamp((t - t0) / 0.04) * fo, lroll=-7)
            y += hgt * 0.90
    return canvas


# ---------------------------------------------------------------- cafe + the vow
def scene_action(t, n, acc):
    canvas = full(t, acc)
    if 26.45 <= t < 27.38:                           # thrown in from the right
        dt = t - 26.45; e = out_expo(dt / 0.16); pm, a = T["hurry"]; xoff = (1 - e) * W * 0.7 - dt * 40 * K
        if e < 0.97:
            kb = int((1 - e) * 120 * K) | 1; pm = cv2.blur(pm, (kb, 1)); a = cv2.blur(a, (kb, 1))
        text_plane(canvas, pm, a, Rmat(-20, 0, 0), W * 0.5 + xoff, H * 0.70, -40, 1.0, clamp(dt / 0.04) * clamp((27.38 - t) / 0.06), lroll=-3)
    if 28.07 <= t < 28.55:                           # ... struck out
        dt = t - 28.07; e = out_expo(dt / 0.12); pm, a = T["worry"]; cx, cy = W * 0.66, H * 0.68
        put(canvas, pm, a, cx, cy, scale=lerp(1.4, 1.0, e), rot=-4, opacity=clamp(dt / 0.04) * clamp((28.55 - t) / 0.05))
        if t >= 28.30:
            u = out_cubic((t - 28.30) / 0.13); half = a.shape[1] * 0.44; x0 = cx - half; x1 = x0 + 2 * half * u
            cv2.line(canvas, (int(x0), int(cy + 8 * K + half * 0.07)), (int(x1), int(cy + 8 * K + half * 0.07 - (x1 - x0) * 0.07)), VRED, max(3, int(22 * K)), cv2.LINE_AA)
    return canvas


def scene_pocket(t, n):
    A = R2.A
    s1, s2 = SH["P1"], SH["P2"]; cur = s1 if t < s2["t0"] else s2
    g0 = tl.CHORUS - 0.55; grow = in_expo((t - g0) / 0.55) if t > g0 else 0.0
    R = Rmat(lerp(9, -5, smooth((t - 28.55) / 1.95)) * (1 - grow), (3 + 1.5 * slow(t, 3)) * (1 - grow), -1.5 * (1 - grow))
    hb = sum(0.022 * math.exp(-(t - b) / 0.10) for b in (28.70, 28.98, 29.60, 29.88) if t >= b)
    cw = int(lerp(W * 0.50, W * 1.03, grow)) // 2 * 2; ch = cw * 9 // 16 // 2 * 2
    e = out_expo((t - 28.55) / 0.22); cx, cy = W * 0.5, lerp(H * 0.42, H * 0.5, grow)
    img = render_shot(cur, t, size=(cw, ch))
    canvas = backdrop(img, 0.13 * (1 - grow)); plus_markers(canvas, R, t, 7.0, 0.3 * (1 - grow))
    card(canvas, img, R, cx, cy, (1 + hb) * lerp(1.12, 1.0, e), "P", A.card_labels["P"], A.card_idx["P"], (1 - grow) * e)
    yb = lerp(cy + ch / 2 + 86 * K, H * 0.70, grow)
    words = list(zip(T["d_prot"], (0.0, 0.50, 0.78))); ov = 25 * K
    x = W * 0.5 - (sum(a.shape[1] for (pm, a), _ in words) - 2 * ov) / 2
    for (pm, a), off in words:                       # thin serif caps, word by word
        if t >= MID + off:
            u = clamp((t - MID - off) / 0.16); put(canvas, pm, a, x + a.shape[1] / 2, yb + (1 - out_cubic(u)) * 10 * K, opacity=u)
        x += a.shape[1] - ov
    words = list(zip(T["d_nmw"], (1.06, 1.18, 1.44))); ov = 20 * K
    x = W * 0.5 - (sum(a.shape[1] for (pm, a), _ in words) - 2 * ov) / 2
    for (pm, a), off in words:                       # bold italic serif, red
        if t >= MID + off:
            u = t - MID - off; e2 = out_expo(u / 0.12); put(canvas, pm, a, x + a.shape[1] / 2, yb + 128 * K, scale=lerp(1.3, 1.0, e2), opacity=clamp(u / 0.04))
        x += a.shape[1] - ov
    return canvas


# ---------------------------------------------------------------- chorus: heavy oblique words in depth
def scene_chorus(t, n, acc):
    if t >= SH["F6"]["t0"]:                           # the last word sits behind Polka, split around his head
        s = SH["F6"]; dt = t - s["t0"]
        canvas = render_shot(s, t, acc).copy(); fg, m = render_shot(s, t, acc, want_matte=True, zmul=1.045)
        e = out_expo(dt / 0.12); j = 6 * K * math.exp(-dt / 0.25); sc_ = lerp(1.5, 1.0, e) * (1 + 0.035 * dt)
        for (pm, a), sg in zip(T["c_en"], (-1, 1)):
            cx = W * 0.5 + sg * W * (0.288 + 0.10 * (1 - e)); cy = H * 0.34 - sg * W * 0.288 * 0.052
            put(canvas, pm, a, cx + j * noise1(t * 3, 1), cy + j * noise1(t * 3, 4), scale=sc_, rot=-3, opacity=clamp(dt / 0.03) * clamp((33.60 - t) / 0.22))
        if m is not None: comp_matte(canvas, fg, m)
        return canvas
    canvas = full(t, acc)
    if t < 30.96:
        slam(canvas, *T["c_aint"], Rmat(28, -5, 0), W * 0.38, H * 0.52, t, tl.CHORUS, lroll=-4)
    elif t < 31.44:
        dt = t - 30.96; sp = out_expo(dt / 0.16) * W * 0.20 + dt * 60 * K; R = Rmat(0, 16, 0)
        for (pm, a), sg in zip(T["c_no"], (-1, 1)):
            slam(canvas, pm, a, R, W * 0.5 + sg * (a.shape[1] * 0.36 + sp), H * 0.5, t, 30.96, lroll=sg * 3.0)
    elif t < 31.89:
        dt = t - 31.44; slam(canvas, *T["c_mount"], Rmat(0, -40, 0), W * 0.5, H * 0.60 - dt * 90 * K, t, 31.44, dz=0, sy=1.7)
    elif t < 32.44:
        dt = t - 31.89
        slam(canvas, *T["c_high"], Rmat(24, 0, 0), W * 0.215, H * 0.56 - out_cubic(dt / 0.5) * H * 0.07, t, 31.89, lroll=-4, sy=1 + 0.9 * out_cubic(dt / 0.45), sc=0.46)
    return canvas


# ---------------------------------------------------------------- outro: the closing line, frame-edge serif
def scene_outro(t, n, acc):
    canvas = np.zeros((H, W, 3), np.uint8); g1 = None
    if t < SH["F6"]["t1"]: canvas = R2.FINALE_HOOK(t, acc) if R2.FINALE_HOOK else render_shot(SH["F6"], t, acc)
    if SH["G1"]["t0"] <= t < SH["G1"]["t1"]:
        img, g1m = render_shot(SH["G1"], t, acc, want_matte=True); g1 = (img, g1m); a = clamp((t - SH["G1"]["t0"]) / SH["G1"]["fin"])
        canvas = img.copy() if a >= 0.999 else cv2.addWeighted(canvas, 1 - a, img, a, 0)
    if t >= SH["G2"]["t0"]:
        img = end_logo_frame(t); a = clamp((t - SH["G2"]["t0"]) / 0.4)
        canvas = img.copy() if a >= 0.999 else cv2.addWeighted(canvas, 1 - a, img, a, 0)
    fo = clamp((36.85 - t) / 0.30)
    if t >= 35.57 and fo > 0:                         # the last word, tucked behind him
        dt = t - 35.57; e = out_expo(dt / 0.22); pm, a = T["peaceful"]
        put(canvas, pm, a, W * 0.66, H * 0.585 + (1 - e) * 30 * K, scale=lerp(0.9, 1.0, e) * (1 + 0.02 * dt), rot=-3, opacity=clamp(dt / 0.12) * fo)
        if g1 is not None and g1[1] is not None:
            k = clamp((SH["G1"]["t1"] - t) / 0.4); comp_matte(canvas, g1[0], cv2.convertScaleAbs(g1[1], alpha=k) if k < 1 else g1[1])
    return canvas


for _n in ("film_text", "scene_verse", "scene_d", "scene_duo", "scene_polaroid", "scene_action", "scene_pocket", "scene_chorus", "scene_outro"):
    setattr(R2, _n, globals()[_n])


def frame_at(n):
    canvas = R2.frame_at(n); t = n / FPS
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
    out = f"{ROOT}/out/{MODE}5_part{wi}.mp4"
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
    with open(f"{ROOT}/out/{MODE}5_parts.txt", "w") as f:
        for p in parts: f.write(f"file '{p}'\n")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{ROOT}/out/{MODE}5_parts.txt", "-c", "copy", f"{ROOT}/out/{MODE}5_video.mp4"], check=True)
    print("wrote", f"{ROOT}/out/{MODE}5_video.mp4", n1 - n0, "frames")
