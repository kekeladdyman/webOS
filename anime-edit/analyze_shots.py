"""Shot detection + per-shot stats + thumbnails from a 480x270 proxy."""
import sys, json, os
import cv2, numpy as np

ep = sys.argv[1]
root = os.path.dirname(os.path.abspath(__file__))
src = f"{root}/proxy/ep{ep}.mp4"
outd = f"{root}/shots/ep{ep}"
os.makedirs(outd, exist_ok=True)

cap = cv2.VideoCapture(src)
fps = cap.get(cv2.CAP_PROP_FPS)
prev_g = None
prev_h = None
motion, hdist, luma, sat = [], [], [], []
n = 0
while True:
    ok, fr = cap.read()
    if not ok:
        break
    small = cv2.resize(fr, (160, 90), interpolation=cv2.INTER_AREA)
    g = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    h = cv2.calcHist([hsv], [0, 1, 2], None, [12, 6, 6], [0, 180, 0, 256, 0, 256]).flatten()
    h /= h.sum() + 1e-9
    if prev_g is None:
        motion.append(0.0); hdist.append(0.0)
    else:
        motion.append(float(cv2.absdiff(g, prev_g).mean()))
        hdist.append(float(np.abs(h - prev_h).sum()))
    luma.append(float(g.mean())); sat.append(float(hsv[..., 1].mean()))
    prev_g, prev_h = g, h
    n += 1
cap.release()
motion = np.array(motion); hdist = np.array(hdist); luma = np.array(luma); sat = np.array(sat)

# cut = big histogram jump that is also a big pixel jump, and a local maximum
cuts = [0]
for i in range(1, n):
    if hdist[i] > 0.55 and motion[i] > 14 and i - cuts[-1] >= 5:
        lo, hi = max(1, i - 3), min(n, i + 4)
        if hdist[i] >= hdist[lo:hi].max() - 1e-9:
            cuts.append(i)
cuts.append(n)

cap = cv2.VideoCapture(src)
shots = []
for k in range(len(cuts) - 1):
    f0, f1 = cuts[k], cuts[k + 1]
    m = motion[f0 + 1:f1] if f1 - f0 > 1 else np.array([0.0])
    shots.append({
        "i": k, "f0": int(f0), "f1": int(f1), "t0": round(f0 / fps, 3), "t1": round(f1 / fps, 3),
        "dur": round((f1 - f0) / fps, 3),
        "mot": round(float(m.mean()), 2), "mot90": round(float(np.percentile(m, 90)), 2),
        "act": round(float((m > 0.6).mean()), 2),
        "luma": round(float(luma[f0:f1].mean()), 1), "sat": round(float(sat[f0:f1].mean()), 1),
    })
    mid = (f0 + f1) // 2
    cap.set(cv2.CAP_PROP_POS_FRAMES, mid)
    ok, fr = cap.read()
    if ok:
        cv2.imwrite(f"{outd}/{k:04d}.jpg", cv2.resize(fr, (240, 135), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 82])
cap.release()
json.dump({"ep": ep, "fps": fps, "n": n, "shots": shots}, open(f"{root}/shots/ep{ep}.json", "w"))
np.save(f"{root}/shots/ep{ep}_motion.npy", motion.astype(np.float32))
print(f"ep{ep}: {n} frames, {len(shots)} shots, fps {fps:.3f}")
