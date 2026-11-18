"""TS=8.1,9.0 OUT=out/x.jpg [RAW=1] python dbg9.py [draft|final] -> contact sheet of render9 frames"""
import os, sys, time
os.environ["TLMOD"] = "tl9"
import render9 as R
import numpy as np, cv2
R.setup9(); ts = [float(x) for x in os.environ["TS"].split(",")]; ims = []; cols = int(os.environ.get("COLS", 3))
for t in ts:
    t0 = time.time(); im = R.frame_at(int(round(t * R.FPS))) if not os.environ.get("RAW") else R.render_t(t); dt = time.time() - t0
    im = cv2.resize(im, (960, 540), interpolation=cv2.INTER_AREA); cv2.putText(im, f"{t:.2f}  {dt:.2f}s", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2, cv2.LINE_AA); ims.append(im)
while len(ims) % cols: ims.append(np.zeros_like(ims[0]))
cv2.imwrite(os.environ.get("OUT", "out/dbg9.jpg"), np.vstack([np.hstack(ims[i:i + cols]) for i in range(0, len(ims), cols)]), [cv2.IMWRITE_JPEG_QUALITY, 85])
