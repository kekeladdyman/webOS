"""V8 compositing toolkit: manga ink + screentone, focus / speed lines, animated panel pages, cut-out puppets
(sticker outline, shadow, echo trails, keyframe tweens), sliced frames, footage-inside-type, duotone, dot disintegration.
Everything works on BGR uint8 images and (premultiplied BGR, alpha) layers, at whatever resolution the frame is."""
import math, numpy as np, cv2

# ---------------------------------------------------------------- easing + keyframes
def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def smooth(u): u = clamp(u); return u * u * (3 - 2 * u)
def ease_out(u, p=3): u = clamp(u); return 1 - (1 - u) ** p
def ease_in(u, p=3): u = clamp(u); return u ** p
def ease_io(u, p=3): u = clamp(u); return 0.5 * (2 * u) ** p if u < 0.5 else 1 - 0.5 * (2 - 2 * u) ** p
def back(u, s=1.9): u = clamp(u) - 1; return u * u * ((s + 1) * u + s) + 1
def elastic(u):
    u = clamp(u)
    return 0.0 if u <= 0 else 1.0 if u >= 1 else 2 ** (-9 * u) * math.sin((u * 10 - 0.75) * 2 * math.pi / 3) + 1
def expo_out(u): u = clamp(u); return 1.0 if u >= 1 else 1 - 2 ** (-10 * u)
def lerp(a, b, u): return a + (b - a) * u
EASE = dict(lin=clamp, smooth=smooth, out=ease_out, inn=ease_in, io=ease_io, back=back, elastic=elastic, expo=expo_out,
            hold=lambda u: 0.0 if u < 1 else 1.0)


def kf(t, keys):
    """keys: [(t, {prop: value}, ease_name_into_this_key), ...] sorted by t. returns dict of props at t (missing props carry over)."""
    st = dict(keys[0][1])
    if t <= keys[0][0]: return st
    for (t0, p0, _), (t1, p1, e) in zip(keys, keys[1:]):
        a = dict(st); a.update(p0); st = a
        if t < t1:
            u = EASE[e or "out"]((t - t0) / max(1e-6, t1 - t0)); out = dict(st)
            for k, v in p1.items():
                v0 = st.get(k, v); out[k] = tuple(lerp(x, y, u) for x, y in zip(v0, v)) if isinstance(v, tuple) else lerp(v0, v, u)
            return out
    st.update(keys[-1][1]); return st


def hrand(*k):
    x = math.sin(sum((i + 1) * 127.1 * float(v) for i, v in enumerate(k))) * 43758.5453
    return x - math.floor(x)


def on2(t, fps_anim=12): return int(t * fps_anim)          # "on twos" frame index for hand-drawn boil


# ---------------------------------------------------------------- tone + ink
_dm = {}


def dotmap(h, w, pitch, angle=45.0, shape="dot"):
    k = (h, w, round(pitch, 2), angle, shape)
    if k not in _dm:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32); a = math.radians(angle)
        u = (xx * math.cos(a) + yy * math.sin(a)) / pitch; v = (-xx * math.sin(a) + yy * math.cos(a)) / pitch
        fu = u - np.floor(u) - 0.5; fv = v - np.floor(v) - 0.5
        _dm[k] = np.sqrt(fu * fu + fv * fv) if shape == "dot" else np.abs(fv)
        if len(_dm) > 24: _dm.pop(next(iter(_dm)))
    return _dm[k]


def halftone(dark, pitch, angle=45.0, shape="dot"):
    """dark (float 0..1) -> ink coverage 0..1 with AM screentone dots (or lines)."""
    d = dotmap(dark.shape[0], dark.shape[1], pitch, angle, shape)
    r = (np.sqrt(np.clip(dark, 0, 1)) * 0.62) if shape == "dot" else np.clip(dark, 0, 1) * 0.5
    soft = 0.9 / max(2.0, pitch)
    return np.clip((r - d) / soft + 0.5, 0, 1)


def levels(gray_f, lo_p=3, hi_p=97):
    lo, hi = np.percentile(gray_f[::5, ::5], (lo_p, hi_p)); return np.clip((gray_f - lo) / max(0.06, hi - lo), 0, 1)


def manga(img, paper=(236, 238, 240), inkc=(14, 12, 14), pitch=None, angle=45.0, solid=0.24, tone_hi=0.70, lines=1.0,
          tone=1.0, line_k=7, keep_glow=0.0, tone_col=None):
    """anime frame -> printed manga panel: clean ink lines, solid blacks, midtones as screentone dots."""
    h, w = img.shape[:2]; k_ = w / 1920.0; pitch = pitch or max(3.0, 7.5 * k_)
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY); g = cv2.bilateralFilter(g, 7, 36, 5 * k_ + 1)
    gf = levels(g.astype(np.float32) / 255.0)
    bs = max(5, int(17 * k_) | 1)
    ln = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, bs, line_k)
    ln = cv2.morphologyEx(255 - ln, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(ln, 8)                  # drop speckles
    small = np.where(st[:, cv2.CC_STAT_AREA] < 28 * k_ * k_ + 4)[0]; small = small[small > 0]
    if len(small): ln[np.isin(lab, small)] = 0
    lnf = cv2.GaussianBlur(ln, (0, 0), 0.6 + 0.5 * k_).astype(np.float32) / 255.0
    dark = 1.0 - gf
    sol = np.clip((dark - (1 - solid)) / 0.05 + 0.5, 0, 1)
    mid = np.clip((dark - (1 - tone_hi)) / max(0.05, tone_hi - solid), 0, 1)
    tn = halftone(mid * 0.85, pitch, angle) * tone
    inkm = np.maximum(np.maximum(sol, lnf * lines), tn if tone_col is None else 0)
    out = np.asarray(paper, np.float32) * (1 - inkm[..., None]) + np.asarray(inkc, np.float32) * inkm[..., None]
    if tone_col is not None:                                                # coloured screentone (a second ink)
        tt = tn * (1 - inkm); out = out * (1 - tt[..., None]) + np.asarray(tone_col, np.float32) * tt[..., None]
    if keep_glow > 0:                                                       # magic / eyes keep their colour
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        kk = np.clip((hsv[..., 1].astype(np.float32) - 90) / 50, 0, 1) * np.clip((hsv[..., 2].astype(np.float32) - 120) / 60, 0, 1)
        kk = (cv2.GaussianBlur(kk, (0, 0), 2 * k_ + 0.5) * keep_glow)[..., None]
        out = out * (1 - kk) + np.clip(img.astype(np.float32) * 1.35, 0, 255) * kk
    return np.clip(out, 0, 255).astype(np.uint8)


def duotone(img, dark, light, mid=None, gamma=1.0, lv=True):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    if lv: g = levels(g, 2, 98)
    if gamma != 1.0: g = g ** gamma
    g = g[..., None]; d, l = np.asarray(dark, np.float32), np.asarray(light, np.float32)
    if mid is None: out = d * (1 - g) + l * g
    else:
        m = np.asarray(mid, np.float32); out = np.where(g < 0.5, d + (m - d) * (g * 2), m + (l - m) * (g * 2 - 1))
    return np.clip(out, 0, 255).astype(np.uint8)


def posterize(img, n=4):
    q = 255.0 / (n - 1); return (np.round(img.astype(np.float32) / q) * q).clip(0, 255).astype(np.uint8)


# ---------------------------------------------------------------- designed backgrounds
def tone_bg(h, w, bg, dot, pitch, angle=45.0, grad=(0.15, 0.85), direction=(0.0, 1.0), shape="dot"):
    """flat colour field with a screentone gradient across it."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32); dx, dy = direction
    p = (xx / w - 0.5) * dx + (yy / h - 0.5) * dy; p = (p - p.min()) / max(1e-6, p.max() - p.min())
    cov = halftone(lerp(grad[0], grad[1], p), pitch, angle, shape)[..., None]
    return np.clip(np.asarray(bg, np.float32) * (1 - cov) + np.asarray(dot, np.float32) * cov, 0, 255).astype(np.uint8)


def radial_tone(h, w, cx, cy, bg, dot, pitch, inner=0.15, outer=1.0, angle=45.0):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32); r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (0.5 * math.hypot(w, h))
    cov = halftone(np.clip((r - inner) / max(1e-3, outer - inner), 0, 1) * 0.9, pitch, angle)[..., None]
    return np.clip(np.asarray(bg, np.float32) * (1 - cov) + np.asarray(dot, np.float32) * cov, 0, 255).astype(np.uint8)


def focus_lines(h, w, cx, cy, seed, n=110, r_in=0.30, r_jit=0.22, width=(0.002, 0.012), ss=2):
    """manga concentration lines (集中線) -> alpha 0..1. Re-seed every 2-3 frames for the hand-drawn boil."""
    rng = np.random.default_rng(int(seed) & 0xFFFFFFFF); hs, ws_ = h // ss, w // ss; m = np.zeros((hs, ws_), np.uint8)
    R = math.hypot(w, h); base = 0.5 * min(w, h); cxs, cys = cx / ss, cy / ss
    for _ in range(n):
        a = rng.uniform(0, 2 * math.pi); wd = rng.uniform(*width) * 2 * math.pi; r0 = (r_in + rng.uniform(0, r_jit)) * base / ss
        tip = (cxs + math.cos(a) * r0, cys + math.sin(a) * r0)
        p1 = (cxs + math.cos(a - wd) * R, cys + math.sin(a - wd) * R); p2 = (cxs + math.cos(a + wd) * R, cys + math.sin(a + wd) * R)
        cv2.fillPoly(m, [np.int32([tip, p1, p2])], 255, cv2.LINE_AA)
    return cv2.resize(m, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32) / 255.0


def speed_lines(h, w, seed, angle=0.0, n=70, length=(0.25, 0.9), thick=(1, 5), cover=1.0, ss=2):
    """parallel motion streaks (for a dash / whip) -> alpha 0..1."""
    rng = np.random.default_rng(int(seed) & 0xFFFFFFFF); D = int(math.hypot(w, h) / ss) + 4; m = np.zeros((D, D), np.uint8)
    for _ in range(n):
        y = rng.uniform(0, D); L = rng.uniform(*length) * D; x = rng.uniform(-0.2 * D, D); t_ = max(1, int(rng.uniform(*thick) * (w / 1920.0) / ss * 2))
        cv2.line(m, (int(x), int(y)), (int(x + L), int(y)), 255, t_, cv2.LINE_AA)
    M = cv2.getRotationMatrix2D((D / 2, D / 2), angle, 1.0); M[0, 2] += (w / ss - D) / 2; M[1, 2] += (h / ss - D) / 2
    m = cv2.warpAffine(m, M, (w // ss, h // ss))
    return cv2.resize(m, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32) / 255.0 * cover


def paint(canvas, col, alpha):
    """canvas = col over canvas with float alpha map (in place)."""
    a = alpha[..., None].astype(np.float32); c = np.asarray(col, np.float32) if np.ndim(col) == 1 else col.astype(np.float32)
    canvas[:] = np.clip(canvas.astype(np.float32) * (1 - a) + c * a, 0, 255).astype(np.uint8); return canvas


# ---------------------------------------------------------------- layers
def to_layer(img, m):
    """(BGR, uint8 matte) -> cropped premult layer + its top-left in source coords."""
    ys, xs = np.where(m > 20)
    if not len(ys): return None
    p = 4; y0, y1 = max(0, ys.min() - p), min(m.shape[0], ys.max() + p); x0, x1 = max(0, xs.min() - p), min(m.shape[1], xs.max() + p)
    a = m[y0:y1, x0:x1].copy(); pm = cv2.multiply(img[y0:y1, x0:x1], cv2.merge([a] * 3), scale=1 / 255.0)
    return dict(pm=pm, a=a, x=x0, y=y0, cx=(x0 + x1) / 2, cy=(y0 + y1) / 2)


def clean_matte(m, k_=1.0, thr=110, feather=1.2, keep_largest=2):
    mb = (m > thr).astype(np.uint8) * 255
    ks = max(3, int(5 * k_) | 1); kk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ks, ks))
    mb = cv2.morphologyEx(cv2.morphologyEx(mb, cv2.MORPH_OPEN, kk), cv2.MORPH_CLOSE, kk)
    if keep_largest:
        n, lab, st, _ = cv2.connectedComponentsWithStats(mb, 8)
        if n > 1:
            order = np.argsort(-st[1:, cv2.CC_STAT_AREA])[:keep_largest] + 1; big = st[order, cv2.CC_STAT_AREA]
            keep = [o for o, b in zip(order, big) if b > 0.08 * big[0]]; mb = np.isin(lab, keep).astype(np.uint8) * 255
    return cv2.GaussianBlur(mb, (0, 0), feather * k_ + 0.3)


def sticker(pm, a, px, col=(250, 250, 250), shadow=None, px2=0, col2=(10, 10, 10)):
    """add a solid outline (and optional 2nd outer outline + drop shadow) under a premult layer."""
    P = int(px + px2 + (shadow[0] * 3 + abs(shadow[1]) + abs(shadow[2]) if shadow else 0)) + 3
    a_ = cv2.copyMakeBorder(a, P, P, P, P, cv2.BORDER_CONSTANT, value=0); pm_ = cv2.copyMakeBorder(pm, P, P, P, P, cv2.BORDER_CONSTANT, value=0)
    af = a_.astype(np.float32) / 255.0; out = np.zeros(pm_.shape, np.float32); al = np.zeros(af.shape, np.float32)
    def over(c, aa):
        nonlocal out, al
        c = np.asarray(c, np.float32); out = c * aa[..., None] + out * (1 - aa[..., None]) if c.ndim == 1 else c + out * (1 - aa[..., None]); al = aa + al * (1 - aa)
    bin_ = (a_ > 100).astype(np.uint8)
    def dil(r):
        k = max(1, int(round(r))) * 2 + 1; return cv2.GaussianBlur(cv2.dilate(bin_, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))).astype(np.float32), (0, 0), 0.8)
    if shadow:
        s_, dx, dy = shadow[:3]; op = shadow[3] if len(shadow) > 3 else 0.6
        sm = cv2.GaussianBlur(dil(px + px2), (0, 0), s_); sm = np.roll(np.roll(sm, int(dy), 0), int(dx), 1); over((0, 0, 0), sm * op)
    if px2: over(col2, dil(px + px2))
    if px: over(col, dil(px))
    over(pm_.astype(np.float32), af)
    return np.clip(out + 0.5, 0, 255).astype(np.uint8), np.clip(al * 255 + 0.5, 0, 255).astype(np.uint8)


def tint_layer(pm, a, col, amt=1.0):
    """recolour a premult layer toward a flat colour (for echo copies / silhouettes)."""
    c = np.asarray(col, np.float32)[None, None] * (a.astype(np.float32)[..., None] / 255.0)
    return np.clip(pm.astype(np.float32) * (1 - amt) + c * amt, 0, 255).astype(np.uint8), a


def lum_layer(pm, a, fn):
    """apply an image op (e.g. manga / duotone) to a layer's colour, keeping its alpha."""
    af = np.maximum(a.astype(np.float32) / 255.0, 1e-3)[..., None]; un = np.clip(pm.astype(np.float32) / af, 0, 255).astype(np.uint8)
    return cv2.multiply(fn(un), cv2.merge([a] * 3), scale=1 / 255.0), a


def place(canvas, pm, a, cx, cy, s=1.0, rot=0.0, op=1.0, sx=1.0, sy=1.0, flip=False):
    """affine-place premult layer with its centre at (cx,cy); fast path when nothing transforms."""
    if op <= 0.003: return
    if flip: pm, a = pm[:, ::-1], a[:, ::-1]
    h, w = a.shape; S = s * sx, s * sy
    c, sn = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    cs = np.array([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]]) * S
    q = np.column_stack([cx + cs[:, 0] * c - cs[:, 1] * sn, cy + cs[:, 0] * sn + cs[:, 1] * c]).astype(np.float32)
    H_, W_ = canvas.shape[:2]
    x0, y0 = int(max(0, math.floor(q[:, 0].min()) - 2)), int(max(0, math.floor(q[:, 1].min()) - 2))
    x1, y1 = int(min(W_, math.ceil(q[:, 0].max()) + 2)), int(min(H_, math.ceil(q[:, 1].max()) + 2))
    if x1 - x0 < 2 or y1 - y0 < 2: return
    M = cv2.getPerspectiveTransform(np.float32([[0, 0], [w, 0], [w, h], [0, h]]), q - np.float32([x0, y0]))
    it = cv2.INTER_AREA if max(S) < 0.7 else cv2.INTER_LINEAR
    wpm = cv2.warpPerspective(pm, M, (x1 - x0, y1 - y0), flags=it); wa = cv2.warpPerspective(a, M, (x1 - x0, y1 - y0), flags=it)
    if op < 0.999: wpm = cv2.convertScaleAbs(wpm, alpha=op); wa = cv2.convertScaleAbs(wa, alpha=op)
    roi = canvas[y0:y1, x0:x1]; cv2.multiply(roi, cv2.merge([255 - wa] * 3), dst=roi, scale=1 / 255.0); cv2.add(roi, wpm, dst=roi)


def place_frame(canvas, img, m, s=1.0, rot=0.0, dx=0.0, dy=0.0, ax=None, ay=None, op=1.0):
    """composite a full-frame cut-out (img + matte, same size as canvas) after an affine about anchor (ax,ay)."""
    H_, W_ = canvas.shape[:2]; ax = W_ / 2 if ax is None else ax; ay = H_ / 2 if ay is None else ay
    M = cv2.getRotationMatrix2D((ax, ay), rot, s); M[0, 2] += dx; M[1, 2] += dy
    wi = cv2.warpAffine(img, M, (W_, H_), flags=cv2.INTER_LINEAR); wm = cv2.warpAffine(m, M, (W_, H_), flags=cv2.INTER_LINEAR)
    if op < 0.999: wm = cv2.convertScaleAbs(wm, alpha=op)
    a3 = cv2.merge([wm] * 3); fg = cv2.multiply(wi, a3, scale=1 / 255.0)
    cv2.multiply(canvas, 255 - a3, dst=canvas, scale=1 / 255.0); cv2.add(canvas, fg, dst=canvas)


def echo(canvas, layer_fn, t, offsets, cols, ops):
    """draw trailing copies: layer_fn(t_past) -> (pm, a, cx, cy, s, rot); copies tinted, drawn back to front."""
    for dt, col, op in zip(offsets, cols, ops):
        pm, a, cx, cy, s, r = layer_fn(t - dt)
        if col is not None: pm, a = tint_layer(pm, a, col)
        place(canvas, pm, a, cx, cy, s, r, op)


# ---------------------------------------------------------------- frame tricks
def poly_mask(h, w, pts, ss=1):
    m = np.zeros((h, w), np.uint8); cv2.fillPoly(m, [np.int32(np.round(pts))], 255, cv2.LINE_AA); return m


def panel(canvas, content, pts, border=6, bcol=(12, 12, 12), op=1.0):
    """content (full-frame BGR) shown inside polygon pts with a black ink border."""
    H_, W_ = canvas.shape[:2]; m = poly_mask(H_, W_, pts)
    if op < 0.999: m = cv2.convertScaleAbs(m, alpha=op)
    a3 = cv2.merge([m] * 3); fg = cv2.multiply(content, a3, scale=1 / 255.0)
    cv2.multiply(canvas, 255 - a3, dst=canvas, scale=1 / 255.0); cv2.add(canvas, fg, dst=canvas)
    if border > 0 and op > 0.3: cv2.polylines(canvas, [np.int32(np.round(pts))], True, bcol, int(border), cv2.LINE_AA)
    return m


def xform_pts(pts, s=1.0, rot=0.0, dx=0.0, dy=0.0, c=None):
    pts = np.asarray(pts, np.float64); c = pts.mean(0) if c is None else np.asarray(c, np.float64)
    a = math.radians(rot); R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    return (pts - c) @ R.T * s + c + np.array([dx, dy])


def warp_to(img, s=1.0, rot=0.0, dx=0.0, dy=0.0, c=None, border=cv2.BORDER_REFLECT_101):
    H_, W_ = img.shape[:2]; c = (W_ / 2, H_ / 2) if c is None else c
    M = cv2.getRotationMatrix2D((float(c[0]), float(c[1])), -rot, s); M[0, 2] += dx; M[1, 2] += dy
    return cv2.warpAffine(img, M, (W_, H_), flags=cv2.INTER_LINEAR, borderMode=border)


def strips(img, n, angle, offs, gap=0, gapcol=(0, 0, 0), bg=None):
    """cut img into n parallel strips at `angle` (deg, 0 = vertical strips) and slide strip i by offs[i] px along the cut."""
    H_, W_ = img.shape[:2]; out = np.zeros_like(img) if bg is None else bg.copy()
    a = math.radians(angle); ux, uy = math.sin(a), math.cos(a)            # direction along the strip
    nx, ny = math.cos(a), -math.sin(a)                                    # across the strips
    yy, xx = np.mgrid[0:H_, 0:W_].astype(np.float32)
    proj = (xx - W_ / 2) * nx + (yy - H_ / 2) * ny; span = abs(W_ * nx) + abs(H_ * ny)
    idx = np.clip(((proj / span + 0.5) * n).astype(np.int32), 0, n - 1)
    for i in range(n):
        M = np.float32([[1, 0, offs[i] * ux], [0, 1, offs[i] * uy]])
        sh = cv2.warpAffine(img, M, (W_, H_), borderMode=cv2.BORDER_REFLECT_101); sel = idx == i
        out[sel] = sh[sel]
    if gap > 0:
        for i in range(1, n):
            p = (i / n - 0.5) * span; c = (W_ / 2 + nx * p, H_ / 2 + ny * p); L = 2 * math.hypot(W_, H_)
            cv2.line(out, (int(c[0] - ux * L), int(c[1] - uy * L)), (int(c[0] + ux * L), int(c[1] + uy * L)), gapcol, int(gap), cv2.LINE_AA)
    return out


def in_type(canvas, footage, mask_full, op=1.0):
    """footage visible only inside a full-frame type mask (uint8)."""
    m = mask_full if op >= 0.999 else cv2.convertScaleAbs(mask_full, alpha=op)
    a3 = cv2.merge([m] * 3); fg = cv2.multiply(footage, a3, scale=1 / 255.0)
    cv2.multiply(canvas, 255 - a3, dst=canvas, scale=1 / 255.0); cv2.add(canvas, fg, dst=canvas)


def mask_full(h, w, mask, cx, cy, s=1.0, rot=0.0):
    """place a cropped alpha mask into a full-frame uint8 mask."""
    mh, mw = mask.shape; M = cv2.getRotationMatrix2D((mw / 2, mh / 2), -rot, s); M[0, 2] += cx - mw / 2; M[1, 2] += cy - mh / 2
    return cv2.warpAffine(mask, M, (w, h), flags=cv2.INTER_LINEAR)


class Dissolve:
    """cut-out that breaks into screentone dots which peel off along a sweep and blow away."""
    def __init__(self, pm, a, pitch=9.0, seed=3, sweep=(1.0, -0.3), rag=0.28):
        self.pm, self.a = pm, a; h, w = a.shape; rng = np.random.default_rng(seed); self.p = pitch
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        fr = (xx / w) * sweep[0] + (yy / h) * sweep[1]; fr = (fr - fr.min()) / max(1e-6, fr.max() - fr.min())
        nz = cv2.resize(rng.uniform(0, 1, (max(2, h // 28), max(2, w // 28))).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
        self.rel = np.clip(fr * (1 - rag) + nz * rag, 0, 1).astype(np.float32)              # release time per pixel
        gy, gx = np.mgrid[pitch / 2:h:pitch, pitch / 2:w:pitch]; gy = gy.ravel().astype(int); gx = gx.ravel().astype(int)
        keep = a[gy, gx] > 110; gy, gx = gy[keep], gx[keep]; self.gx, self.gy = gx.astype(np.float32), gy.astype(np.float32)
        af = np.maximum(a[gy, gx].astype(np.float32) / 255.0, 1e-3)[:, None]; self.col = np.clip(pm[gy, gx].astype(np.float32) / af, 0, 255)
        self.r_ = self.rel[gy, gx]; n = len(gx)
        self.v = np.stack([rng.uniform(0.5, 1.4, n), rng.uniform(-0.6, 0.4, n)], 1).astype(np.float32)
        self.life = rng.uniform(0.18, 0.40, n).astype(np.float32)
    def draw(self, canvas, u, cx, cy, s=1.0, drift=(520.0, -260.0), op=1.0, tint=None):
        h, w = self.a.shape; keep = (self.rel > u * 1.25).astype(np.float32)
        edge = np.clip((self.rel - u * 1.25) / 0.03, 0, 1)
        a2 = (self.a.astype(np.float32) * keep * edge).astype(np.uint8)
        if a2.max() > 0:
            # the intact part shows its screentone near the breaking edge
            near = np.clip(1 - (self.rel - u * 1.25) / 0.10, 0, 1) * (u > 0.001)
            cov = halftone(1 - near * 0.8, self.p, 45.0); a2 = (a2.astype(np.float32) * np.where(near > 0, cov, 1)).astype(np.uint8)
            pm2 = cv2.multiply(self.pm, cv2.merge([a2] * 3), scale=1 / 255.0)
            af = np.maximum(self.a.astype(np.float32) / 255.0, 1e-3)[..., None]; pm2 = np.clip(pm2.astype(np.float32) / af, 0, 255).astype(np.uint8)
            place(canvas, pm2, a2, cx, cy, s, 0, op)
        age = (u * 1.25 - self.r_) / self.life; sel = (age > 0) & (age < 1)
        if not sel.any(): return
        ag = age[sel]; e = ag ** 1.4
        px = cx + ((self.gx[sel] - w / 2) + self.v[sel, 0] * drift[0] * e) * s; py = cy + ((self.gy[sel] - h / 2) + (self.v[sel, 1] * 0.4 + 1.0) * drift[1] * e * 0.6 + self.v[sel, 1] * 80 * e) * s
        rad = (self.p * 0.5 * (1 - ag) ** 0.8) * s; col = self.col[sel] if tint is None else np.broadcast_to(np.asarray(tint, np.float32), (sel.sum(), 3))
        H_, W_ = canvas.shape[:2]; ok = (px > -10) & (px < W_ + 10) & (py > -10) & (py < H_ + 10) & (rad > 0.6)
        for x_, y_, r_, c_ in zip(px[ok], py[ok], rad[ok], col[ok]):
            cv2.circle(canvas, (int(x_ * 4), int(y_ * 4)), int(r_ * 4), tuple(float(v) * op for v in c_), -1, cv2.LINE_AA, 2)


def shake(t, amp, seed=1.0, f=1.0):
    return (amp * (math.sin(t * 37.1 * f + seed * 12.9) + 0.6 * math.sin(t * 71.7 * f + seed * 4.1)) / 1.6,
            amp * (math.sin(t * 41.3 * f + seed * 7.3) + 0.6 * math.sin(t * 67.9 * f + seed * 2.9)) / 1.6)


def impact_frames(img, t, t0, n=2, fps=60, cols=((250, 250, 250), (14, 10, 12))):
    """the 1-2 frame black/white inversion flash used on hits."""
    k = int((t - t0) * fps)
    if not (0 <= t - t0 < n / fps): return img
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY); thr = float(np.percentile(g[::8, ::8], 60)); m = g > thr
    out = np.empty_like(img); a, b = (cols if k % 2 == 0 else cols[::-1]); out[:] = b; out[m] = a; return out


# ---------------------------------------------------------------- v23: tone-mapped inks (dark shots become readable line art)
def tonemap(img, target=0.52, gmin=0.38, gmax=1.5):
    f = img.astype(np.float32); g = f.mean(2); lo, hi = np.percentile(g[::4, ::4], (1.0, 99.6)); x = np.clip((f - lo) / max(10.0, hi - lo), 0, 1)
    med = float(np.clip(np.median(x.mean(2)[::4, ::4]), 0.02, 0.98)); gam = float(np.clip(math.log(target) / math.log(med), gmin, gmax))
    return (np.power(x, gam) * 255).astype(np.uint8)


def ink2(img, accent=None, glow=0.0, solid=0.22, tone_hi=0.66, paper=(236, 238, 240), inkc=(14, 12, 14), line_k=7, pitch=None, target=0.52):
    """the page look: tone-map, then clean ink + screentone. accent = second ink colour for the screentone; glow keeps saturated light in colour."""
    tm = tonemap(img, target); out = manga(tm, paper=paper, inkc=inkc, solid=solid, tone_hi=tone_hi, tone_col=accent, line_k=line_k, pitch=pitch)
    if glow > 0:
        k_ = img.shape[1] / 1920.0; hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        kk = np.clip((hsv[..., 1].astype(np.float32) - 95) / 50, 0, 1) * np.clip((hsv[..., 2].astype(np.float32) - 125) / 60, 0, 1)
        kk = (cv2.GaussianBlur(kk, (0, 0), 2 * k_ + 0.5) * glow)[..., None]
        out = np.clip(out * (1 - kk) + np.clip(img.astype(np.float32) * 1.3, 0, 255) * kk, 0, 255).astype(np.uint8)
    return out
