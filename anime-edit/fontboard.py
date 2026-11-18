import subprocess, numpy as np, cv2, math, sys
import fxtype as F
from rembg import new_session, remove
W, H = 1920, 1080
SESS = None


def frame(ep, t):
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", f"eps/ep{ep:02d}.mkv", "-frames:v", "1", "-vf", "scale=1920:1080", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    return np.frombuffer(p, np.uint8).reshape(H, W, 3).copy()


def matte(img):
    global SESS
    if SESS is None: SESS = new_session("isnet-anime")
    return np.array(remove(img, session=SESS, only_mask=True))


def comp(canvas, layer, x, y, op=1.0):
    pm, a = layer; h, w = a.shape; x0, y0 = int(x), int(y); xa, ya = max(0, x0), max(0, y0); xb, yb = min(W, x0 + w), min(H, y0 + h)
    if xa >= xb or ya >= yb: return
    pm = pm[ya - y0:yb - y0, xa - x0:xb - x0].astype(np.float32) * op; a = a[ya - y0:yb - y0, xa - x0:xb - x0].astype(np.float32) / 255.0 * op
    roi = canvas[ya:yb, xa:xb].astype(np.float32); canvas[ya:yb, xa:xb] = np.clip(roi * (1 - a[..., None]) + pm, 0, 255).astype(np.uint8)


def warp_layer(layer, quad):
    """put a layer on an arbitrary screen quad (tl,tr,br,bl) -> full-frame layer."""
    pm, a = layer; h, w = a.shape; M = cv2.getPerspectiveTransform(np.float32([[0, 0], [w, 0], [w, h], [0, h]]), np.float32(quad))
    return cv2.warpPerspective(pm, M, (W, H), flags=cv2.INTER_LINEAR), cv2.warpPerspective(a, M, (W, H), flags=cv2.INTER_LINEAR)


def rot_layer(layer, deg, scale=1.0):
    pm, a = layer; h, w = a.shape; c = (w / 2, h / 2); M = cv2.getRotationMatrix2D(c, deg, scale)
    cs, sn = abs(M[0, 0]), abs(M[0, 1]); nw, nh = int(h * sn + w * cs) + 4, int(h * cs + w * sn) + 4; M[0, 2] += nw / 2 - c[0]; M[1, 2] += nh / 2 - c[1]
    return cv2.warpAffine(pm, M, (nw, nh), flags=cv2.INTER_LINEAR), cv2.warpAffine(a, M, (nw, nh), flags=cv2.INTER_LINEAR)


def fit(layer, width):
    pm, a = layer; s = width / a.shape[1]; return cv2.resize(pm, None, fx=s, fy=s, interpolation=cv2.INTER_AREA), cv2.resize(a, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)


def label(img, n, name, role):
    cv2.rectangle(img, (0, 0), (W, 64), (0, 0, 0), -1)
    cv2.putText(img, f"{n}", (18, 50), cv2.FONT_HERSHEY_DUPLEX, 1.6, (80, 230, 250), 2, cv2.LINE_AA)
    cv2.putText(img, f"{role}  -  {name}", (90, 44), cv2.FONT_HERSHEY_SIMPLEX, 1.05, (240, 240, 240), 2, cv2.LINE_AA)
    return img


def grade(img, k=0.85): return cv2.convertScaleAbs(img, alpha=k, beta=-6)


tiles = []
# 1  JPOXI 3D glow word, in perspective
img = grade(frame(1, 1029.9), 0.75); L = F.metal3d(F.glyphs("UNMASKED", "texgyreheroscn-bold.otf", 300, tracking=-4), top=(235, 255, 205), bot=(160, 190, 95),
         depth=0.16, angle=28, ext=(80, 95, 25), ext_far=(22, 30, 8), glow=((200, 235, 40), 30, 0.65), spec=0.22)
L = fit(L, 1100); h, w = L[1].shape; L = warp_layer(L, [(120, 610), (1180, 520), (1220, 820), (90, 930)]); comp(img, L, 0, 0)
tiles.append(label(img, 1, "TeX Gyre Heros Condensed Bold Italic  (3D extrude + glow)", "JPOXI impact word"))
# 2  JPOXI brushed metal
img = grade(frame(1, 425.5), 0.8); L = F.metal3d(F.glyphs("FACE", "texgyreheroscn-bolditalic.otf", 340, tracking=-4), top=(245, 248, 250), bot=(110, 112, 118),
         depth=0.06, angle=40, ext=(60, 60, 66), ext_far=(18, 18, 20), spec=0.75, noise=6, glow=((255, 255, 255), 30, 0.18))
L = fit(L, 820); comp(img, L, 1020, 380)
tiles.append(label(img, 2, "TeX Gyre Heros Condensed Bold Italic  (brushed metal)", "JPOXI impact word"))
# 3  Clash Display chrome, behind the character
img = grade(frame(1, 1107.4), 0.95); m = matte(img); L = fit(F.chrome(F.glyphs("DEMONS", "ClashDisplay-Bold.otf", 300, tracking=2), c1=(205, 190, 60), c2=(255, 255, 245), c3=(120, 90, 20), ext=(70, 50, 10), glow=((220, 200, 60), 26, 0.30)), 1600)
fg = img.copy(); comp(img, L, 160, 300); a3 = cv2.merge([m] * 3).astype(np.float32) / 255; img = (img * (1 - a3) + fg * a3).astype(np.uint8)
tiles.append(label(img, 3, "Clash Display Bold  (chrome, behind him)", "JPOXI impact word"))
# 4  VRENS stack, Barlow Condensed Black Italic
img = grade(frame(1, 594.5), 0.95)
lines = [F.glyphs(s_, "BarlowCondBlackItalic.ttf", 230, tracking=2) for s_ in ("WHO", "ARE", "YOU?")]
layers = [F.vrens(m_, fill=c_) for m_, c_ in zip(lines, ((250, 250, 250), (40, 30, 235), (250, 250, 250)))]
y = 300
for i, Lr in enumerate(layers):
    Lr = rot_layer(fit(Lr, [520, 460, 640][i]), 9); comp(img, Lr, 120 + i * 30, y); y += Lr[1].shape[0] * 0.62
tiles.append(label(img, 4, "Barlow Condensed Black Italic  (VRENS stack, white / red)", "VRENS stacked line"))
# 5  VRENS stack, Tanker
img = grade(frame(1, 651.5), 0.85)
lines = [F.glyphs(s_, "Tanker-Regular.otf", 210, tracking=4) for s_ in ("THIS BODY", "ISN'T", "MINE")]
layers = [F.vrens(m_, fill=c_, depth=0.12) for m_, c_ in zip(lines, ((250, 250, 250), (250, 250, 250), (40, 30, 235)))]
y = 330
for i, Lr in enumerate(layers):
    Lr = rot_layer(fit(Lr, [760, 380, 560][i]), -7); comp(img, Lr, 640 + i * 20, y); y += Lr[1].shape[0] * 0.70
tiles.append(label(img, 5, "Tanker  (VRENS stack)", "VRENS stacked line"))
# 6  giant cropped letters behind him (Vinland / Aidour)
img = grade(frame(1, 597.4), 0.9); m = matte(img)
L = F.metal3d(F.glyphs("SHINJUKU", "CabinetGrotesk-Black.otf", 520, tracking=-10), top=(250, 250, 250), bot=(200, 200, 205), depth=0.05, ext=(120, 120, 130), ext_far=(60, 60, 70), spec=0.2, shadow=0.4)
L = fit(L, 2300); fg = img.copy(); comp(img, L, -190, 300, 0.95); a3 = cv2.merge([m] * 3).astype(np.float32) / 255; img = (img * (1 - a3) + fg * a3).astype(np.uint8)
tiles.append(label(img, 6, "Cabinet Grotesk Black  (giant, cropped, behind him)", "VRENS stacked line"))
# 7  JPOXI title card
img = grade(frame(5, 406.6), 1.0)
t1 = fit(F.flat(F.glyphs("POLKA SHINOYAMA", "texgyreheros-bold.otf", 160, tracking=-2), (245, 245, 245), glow=((255, 230, 220), 18, 0.35), shadow=(12, 0.8, 6)), 1320)
t2 = fit(F.flat(F.glyphs("THE CORPSE GOD", "texgyreheroscn-bold.otf", 80, tracking=14), (240, 240, 240), shadow=(8, 0.7, 3)), 420)
comp(img, t1, W / 2 - t1[1].shape[1] / 2, 640); comp(img, t2, W / 2 - t2[1].shape[1] / 2, 640 + t1[1].shape[0] - 30)
bl = F.stack([F.glyphs(x_, "texgyreheroscn-bold.otf", 40, tracking=2) for x_ in ("AN EDIT BY SHIGAMI. CUT TO “SYNTHETIC”. FOOTAGE FROM DEAD MOUNT DEATH PLAY,", "EPISODES 01 02 04 05. BASED ON THE MANGA BY RYOHGO NARITA AND SHINTA FUJIMOTO.", "NO ONE IS WHO THEY SAY THEY ARE.")], gap=0.35, align="center")
b = fit(F.flat(bl, (215, 215, 215)), 640); comp(img, b, W / 2 - b[1].shape[1] / 2, 905)
tiles.append(label(img, 7, "TeX Gyre Heros Bold + Condensed  (JPOXI title card)", "Title card"))
# 8  VRENS Didone card
img = np.zeros((H, W, 3), np.uint8); img[:] = 6
t1 = fit(F.flat(F.glyphs("NECROMANCER", "LibreBodoniItalic.ttf", 220, tracking=6, var=[700]), (40, 30, 235), glow=((60, 40, 255), 20, 0.25)), 1300)
comp(img, t1, W / 2 - t1[1].shape[1] / 2, H / 2 - t1[1].shape[0] / 2)
tiles.append(label(img, 8, "Libre Bodoni Bold Italic  (VRENS 'KATON' card)", "Title card"))
# 9  MARATHON techno title over the eye
img = grade(frame(1, 688.6), 0.7); g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY); img = cv2.addWeighted(img, 0.5, cv2.merge([g] * 3), 0.5, 0)
t1 = fit(F.flat(F.glyphs("SYNTHETIC", "BigShouldersStencil.ttf", 360, tracking=4, var=[850]), (40, 240, 225), shadow=(10, 0.6, 4)), 1250)
comp(img, t1, W / 2 - t1[1].shape[1] / 2, 380)
mono = fit(F.flat(F.glyphs("SHIGAMI  ×  DMDP   //   28.93   //   “WHO IS WEARING HIS FACE”", "SpaceMono.ttf", 26, tracking=3), (40, 240, 225)), 900)
comp(img, mono, W / 2 - t1[1].shape[1] / 2, 380 + t1[1].shape[0] + 20)
tiles.append(label(img, 9, "Big Shoulders Stencil  (MARATHON title)", "Title card"))
# 10-12  MARATHON lyric serif on a tilted frame
for n, (fnt, var, nm) in enumerate((("Zodiak-Thin.otf", None, "Zodiak Thin"), ("Italiana.ttf", None, "Italiana"), ("Boska-Light.otf", None, "Boska Light")), 10):
    src = grade(frame(1, 651.5), 0.9); img = np.zeros((H, W, 3), np.uint8); img[:] = 8
    cw, ch = 1150, 646; card = cv2.resize(src, (cw, ch)); quad = [(380, 180), (1500, 230), (1470, 860), (400, 830)]
    M = cv2.getPerspectiveTransform(np.float32([[0, 0], [cw, 0], [cw, ch], [0, ch]]), np.float32(quad))
    img = np.maximum(img, cv2.warpPerspective(card, M, (W, H)))
    cv2.polylines(img, [np.int32([(350, 150), (1535, 200), (1505, 895), (370, 860)])], True, (200, 200, 200), 2, cv2.LINE_AA)
    l1 = F.glyphs("I DON'T EVEN", fnt, 170, tracking=0, var=var); l2 = F.glyphs("RECOGNIZE MYSELF", fnt, 170, tracking=0, var=var)
    st = F.stack([l1, l2], gap=0.22, align="center"); L = fit(F.flat(st, (40, 240, 220), shadow=(10, 0.7, 4)), 1180); comp(img, L, W / 2 - L[1].shape[1] / 2, 600)
    tiles.append(label(img, n, f"{nm}  (MARATHON lyric serif)", "Dialogue / lyric serif"))

for b_ in range(2):
    sel = tiles[b_ * 6:(b_ + 1) * 6]; sel = [cv2.resize(x, (960, 540), interpolation=cv2.INTER_AREA) for x in sel]
    board = np.vstack([np.hstack(sel[i:i + 2]) for i in range(0, 6, 2)])
    cv2.imwrite(f"out/fontboard_{b_ + 1}.jpg", board, [cv2.IMWRITE_JPEG_QUALITY, 90])
print("ok")
