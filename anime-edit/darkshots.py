"""Sensitive shot detection for dark scenes + brightened contact sheet. usage: darkshots.py EP t0 t1 name"""
import sys, json, cv2, numpy as np
ep, t0, t1, name = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
cap = cv2.VideoCapture(f"proxy/ep{ep}.mp4"); fps = cap.get(cv2.CAP_PROP_FPS)
f0, f1 = int(t0 * fps), int(t1 * fps); cap.set(cv2.CAP_PROP_POS_FRAMES, f0)
fr = []; mot = [0.0]; hd = [0.0]; pg = ph = None
for i in range(f0, f1):
    ok, f = cap.read()
    if not ok: break
    fr.append(cv2.resize(f, (160, 90), interpolation=cv2.INTER_AREA))
    g = cv2.cvtColor(fr[-1], cv2.COLOR_BGR2GRAY).astype(np.float32); g = g / (g.mean() + 6.0) * 40.0          # exposure-normalised
    h = cv2.calcHist([np.clip(g, 0, 255).astype(np.uint8)], [0], None, [32], [0, 256]).flatten(); h /= h.sum() + 1e-9
    if pg is not None: mot.append(float(np.abs(g - pg).mean())); hd.append(float(np.abs(h - ph).sum()))
    pg, ph = g, h
mot = np.array(mot); hd = np.array(hd); n = len(fr)
cuts = [0]
for i in range(1, n):
    if mot[i] > 9.0 and hd[i] > 0.30 and i - cuts[-1] >= 6 and mot[i] >= mot[max(1, i - 3):min(n, i + 4)].max() - 1e-9: cuts.append(i)
cuts.append(n)
shots = []
for a, b in zip(cuts, cuts[1:]):
    m = mot[a + 1:b] if b - a > 1 else np.array([0.0])
    shots.append(dict(t0=round(t0 + a / fps, 2), dur=round((b - a) / fps, 2), mot=round(float(m.mean()), 1), mid=(a + b) // 2, a=a, b=b))
json.dump(shots, open(f"shots/dark_{name}.json", "w"))
TW, TH, LH, COLS = 160, 90, 13, 12
tiles = []
for s in shots:
    for k, fi in enumerate([s["mid"]] if s["dur"] < 3.0 else list(np.linspace(s["a"] + 6, s["b"] - 6, int(min(6, s["dur"] // 1.6 + 1))).astype(int))):
        im = fr[min(fi, n - 1)].astype(np.float32) / 255.0
        im = np.clip((im ** 0.5) * 255 * 1.15, 0, 255).astype(np.uint8)                                              # brighten for review
        t = t0 + fi / fps; m_, s_ = divmod(t, 60)
        tile = np.zeros((TH + LH, TW, 3), np.uint8); tile[:TH] = im
        col = (120, 255, 120) if s["mot"] > 6 else (255, 255, 255)
        cv2.putText(tile, f"{int(m_)}:{s_:04.1f} d{s['dur']:.1f} m{s['mot']:.0f}" if k == 0 else f"{int(m_)}:{s_:04.1f} ..", (2, TH + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.34, col, 1, cv2.LINE_AA)
        tiles.append(tile)
rows = (len(tiles) + COLS - 1) // COLS
while len(tiles) < rows * COLS: tiles.append(np.zeros_like(tiles[0]))
img = np.vstack([np.hstack(tiles[r * COLS:(r + 1) * COLS]) for r in range(rows)])
cv2.imwrite(f"sheets/dark_{name}.jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 82]); print(name, len(shots), "shots", len(tiles), "tiles", img.shape)
