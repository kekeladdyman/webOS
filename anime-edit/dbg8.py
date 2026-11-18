"""TS=8.1,9.0 OUT=out/x.jpg python dbg8.py [draft|final] -> contact sheet of render8 frames"""
import os, sys, time
os.environ["TLMOD"] = "tl8"
import render8 as R
import numpy as np, cv2
R.setup8(); ts = [float(x) for x in os.environ["TS"].split(",")]; ims = []
for t in ts:
    t0 = time.time(); im = R.frame_at(int(round(t * R.FPS))); dt = time.time() - t0
    im = cv2.resize(im, (960, 540), interpolation=cv2.INTER_AREA); cv2.putText(im, f"{t:.2f}  {dt:.2f}s", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2, cv2.LINE_AA); ims.append(im)
while len(ims) % 3: ims.append(np.zeros_like(ims[0]))
cv2.imwrite(os.environ.get("OUT", "out/dbg8.jpg"), np.vstack([np.hstack(ims[i:i + 3]) for i in range(0, len(ims), 3)]), [cv2.IMWRITE_JPEG_QUALITY, 85])
