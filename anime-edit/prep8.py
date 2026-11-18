"""re-matte the dark shots: rembg on a brightened copy, or a luminance key where rembg can't see the figure (skull, bandaged face)."""
import os, sys, numpy as np, cv2, time
os.environ.setdefault("TLMOD", "tl8")
import tl8, extract
from rembg import new_session, remove
sess = new_session("isnet-anime")
def bright(f, g=0.55):
    lo, hi = np.percentile(f[::4, ::4], (1, 99.5)); x = np.clip((f.astype(np.float32) - lo) / max(8, hi - lo), 0, 1) ** g
    return (x * 255).astype(np.uint8)
def lumkey(f, pct, close=21):
    g = cv2.GaussianBlur(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), (0, 0), 2.0).astype(np.float32); thr = np.percentile(g[::4, ::4], pct)
    m = (np.clip((g - thr) / 18.0, 0, 1) * 255).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close, close)))
    n, lab, st, _ = cv2.connectedComponentsWithStats((m > 128).astype(np.uint8), 8)
    if n > 1:
        keep = np.argsort(-st[1:, cv2.CC_STAT_AREA])[:3] + 1; big = st[keep, cv2.CC_STAT_AREA]; keep = [k for k, b in zip(keep, big) if b > 0.1 * big[0]]
        m = (m * np.isin(lab, keep)).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close * 2 + 1, close * 2 + 1)))
    return m
JOBS = {"PF": ("bright", 0.55), "L5": ("bright", 0.55), "S4": ("bright", 0.55), "D10": ("bright", 0.55), "D2b": ("bright", 0.55),
        "V2": ("lum", 62), "W1": ("lum", 74)}
for nm, (how, p) in JOBS.items():
    if len(sys.argv) > 1 and nm not in sys.argv[1:]: continue
    s = tl8.BY[nm]; k = extract.key(s); cap = cv2.VideoCapture(f"cache/{k}.mp4"); ms = []; prev = pm = None; t0 = time.time()
    while True:
        ok, f = cap.read()
        if not ok: break
        if prev is not None and np.abs(f[::6, ::6].astype(np.int16) - prev[::6, ::6]).mean() < 0.35: ms.append(pm); continue
        m = np.array(remove(bright(f, p), session=sess, only_mask=True, post_process_mask=False)) if how == "bright" else lumkey(f, p)
        prev, pm = f, m; ms.append(m)
    np.savez_compressed(f"mattes/{k}.npz", m=np.stack(ms)); print(nm, how, len(ms), "frames", round(time.time() - t0, 1), "s cover", round(float((np.stack(ms) > 128).mean()), 3), flush=True)
