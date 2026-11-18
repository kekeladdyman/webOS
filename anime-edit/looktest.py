import os, sys
os.environ["TLMOD"] = "tl8"; sys.argv = [sys.argv[0], "draft"]
import render8 as R, fxcomp as X, numpy as np, cv2
names = "V4 V5a V5b V6 V7 V8 V9 D2b D1 D3 D4 D5 D6 D9 D10 W1 L2 L3 L4 L5 L6 S1 S2 S3 S4 S5 F6 O1a O1b O2 O3 O4 O5 PF".split()
rows = []
for nm in names:
    s = R.SH[nm]; t = s["t0"] + 0.4 * (s["t1"] - s["t0"]); raw = R.base(nm, t, "raw")
    a = X.ink2(raw); b = X.ink2(raw, accent=(40, 30, 215), glow=1.0); c = X.ink2(raw, glow=1.0, solid=0.30, tone_hi=0.74)
    r = np.hstack([cv2.resize(x, (480, 270), interpolation=cv2.INTER_AREA) for x in (raw, a, b, c)]); cv2.putText(r, nm, (8, 26), 0, 0.9, (0, 255, 255), 2); rows.append(r)
for i in range(0, len(rows), 9): cv2.imwrite(f"out/looks_{i // 9}.jpg", np.vstack(rows[i:i + 9]), [cv2.IMWRITE_JPEG_QUALITY, 85])
