import sys, time, traceback
sys.argv = ["x", "draft"]
import render2 as r, cv2, numpy as np
r.A = r.Assets(); print("assets ok")
ts = [float(x) for x in sys.argv[1:]] if False else None
import os
times = [0.8, 2.1, 2.9, 4.5, 5.7, 6.3, 7.5, 8.8, 9.4, 9.9, 10.7, 11.3, 11.8, 12.4, 12.9, 13.6, 14.3, 15.0, 16.4, 17.4, 18.2, 19.0, 19.9, 21.0, 21.6, 22.3, 23.6, 24.6, 25.4, 25.7, 26.0, 26.9, 28.2, 28.9, 29.5, 30.3, 30.7, 31.2, 31.7, 32.2, 33.2, 34.5, 35.9, 36.5, 37.4, 38.2]
if len(os.environ.get("TS", "")): times = [float(x) for x in os.environ["TS"].split(",")]
fr = []; t0 = time.time()
for t in times:
    try:
        f = r.frame_at(int(round(t * r.FPS)))
    except Exception:
        print("ERR at", t); traceback.print_exc(); f = np.zeros((r.H, r.W, 3), np.uint8)
    f = cv2.resize(f, (384, 216), interpolation=cv2.INTER_AREA)
    cv2.putText(f, f"{t:.2f}", (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA); fr.append(f)
print("avg s/frame", round((time.time() - t0) / len(times), 3))
cols = 5; rows = (len(fr) + cols - 1) // cols
while len(fr) < rows * cols: fr.append(np.zeros_like(fr[0]))
cv2.imwrite(os.environ.get("OUT", "out/dbg2.jpg"), np.vstack([np.hstack(fr[i * cols:(i + 1) * cols]) for i in range(rows)]), [cv2.IMWRITE_JPEG_QUALITY, 86])
