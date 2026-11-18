import subprocess, numpy as np, cv2, time, sys
import fxcomp as X
from rembg import new_session, remove
W, H = 1920, 1080; SESS = new_session("isnet-anime")
def frame(ep, t):
    p = subprocess.run(["ffmpeg","-v","error","-ss",str(t),"-i",f"eps/ep{ep:02d}.mkv","-frames:v","1","-vf","scale=1920:1080","-f","rawvideo","-pix_fmt","bgr24","-"],capture_output=True).stdout
    return np.frombuffer(p,np.uint8).reshape(H,W,3).copy()
def matte(img): return np.array(remove(img, session=SESS, only_mask=True))
tiles = []; T = time.time()
a = frame(1, 682.95); t0 = time.time(); m1 = X.manga(a); print("manga", round(time.time()-t0, 3)); tiles.append(m1)
b = frame(1, 506.85); tiles.append(X.manga(b, keep_glow=1.0, solid=0.30))
# Misaki cut-out on a red tone field with focus lines + sticker outline
c = frame(1, 1029.9); mc = X.clean_matte(matte(c)); L = X.to_layer(c, mc)
bg = X.tone_bg(H, W, (40, 30, 225), (10, 8, 12), 9.0, 45, (0.05, 0.9), (0.6, 0.8))
fl = X.focus_lines(H, W, W*0.42, H*0.45, 7, n=130); X.paint(bg, (10, 8, 12), fl * 0.85)
pm, al = X.sticker(L["pm"], L["a"], 9, (250, 250, 250), shadow=(10, 18, 22, 0.7), px2=5, col2=(12, 10, 12))
for k, (dx, col, op) in enumerate(((-140, (250, 250, 250), 0.5), (-70, (12, 10, 12), 0.7))):
    tp, ta = X.tint_layer(pm, al, col); X.place(bg, tp, ta, L["cx"] + dx, L["cy"], 1.0, 0, op)
X.place(bg, pm, al, L["cx"], L["cy"], 1.0, -3); tiles.append(bg)
# Polka cut-out in manga ink breaking out of a panel
d = frame(1, 594.5); md = X.clean_matte(matte(d)); page = np.full((H, W, 3), 240, np.uint8)
pts = [(120, 90), (1250, 140), (1180, 990), (160, 960)]; ink = X.manga(d, tone_col=(40, 30, 225))
X.panel(page, X.warp_to(ink, 1.1), pts, border=10)
X.panel(page, X.manga(frame(1, 651.2)), [(1300, 120), (1820, 90), (1840, 520), (1290, 560)], border=10)
X.panel(page, X.manga(frame(5, 342.4), keep_glow=1.0), [(1290, 610), (1840, 580), (1800, 990), (1280, 1000)], border=10)
Ld = X.to_layer(X.warp_to(ink, 1.1), X.warp_to(md, 1.1, border=cv2.BORDER_CONSTANT)); X.place(page, *X.sticker(Ld["pm"], Ld["a"], 0)[:2], Ld["cx"] + 120, Ld["cy"] - 20, 1.06)
tiles.append(page)
# strips on the fire battlefield
e = frame(1, 381.8); tiles.append(X.strips(e, 7, 18, [(-1) ** i * 120 * (1 + i % 3) for i in range(7)], gap=10))
# disintegrate Polka (outro)
f = frame(1, 646.5); mf = X.clean_matte(matte(f)); Lf = X.to_layer(f, mf); bgf = X.duotone(f, (30, 16, 20), (200, 210, 225))
bgf[:] = (bgf * 0.4).astype(np.uint8); t0 = time.time(); dp, da = X.disintegrate(Lf["pm"], Lf["a"], 0.55, pitch=9, drift=(380, -160)); print("disint", round(time.time()-t0, 2))
X.place(bgf, dp, da, Lf["cx"], Lf["cy"]); tiles.append(bgf)
np.save("cut/test_mattes.npy", np.stack([mc, md, mf]))
sel = [cv2.resize(x, (960, 540), interpolation=cv2.INTER_AREA) for x in tiles]
cv2.imwrite("out/fxtest.jpg", np.vstack([np.hstack(sel[i:i+2]) for i in range(0, 6, 2)]), [cv2.IMWRITE_JPEG_QUALITY, 88]); print("total", round(time.time()-T, 1))
