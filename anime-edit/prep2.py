"""Extract v2 clips + compute character mattes for shots flagged matte=True."""
import os, sys, numpy as np, cv2, time
from concurrent.futures import ThreadPoolExecutor
import importlib, extract
tl2 = importlib.import_module(os.environ.get('TLMOD', 'tl2'))
os.makedirs(f"{tl2.ROOT}/mattes", exist_ok=True)
with ThreadPoolExecutor(3) as ex: outs = list(ex.map(extract.run, tl2.SHOTS))
print(len(set(outs)), "clips", flush=True)
from rembg import new_session, remove
sess = new_session("isnet-anime")
for s in tl2.SHOTS:
    if not s["matte"]: continue
    k = extract.key(s); out = f"{tl2.ROOT}/mattes/{k}.npz"
    if os.path.exists(out): continue
    cap = cv2.VideoCapture(f"{tl2.ROOT}/cache/{k}.mp4"); ms = []; t0 = time.time(); prev = None; pm = None
    while True:
        ok, f = cap.read()
        if not ok: break
        if prev is not None and np.abs(f[::6, ::6].astype(np.int16) - prev[::6, ::6]).mean() < 0.35: ms.append(pm); continue   # held anime frame
        m = np.array(remove(f, session=sess, only_mask=True, post_process_mask=False))
        prev, pm = f, m; ms.append(m)
    np.savez_compressed(out, m=np.stack(ms)); print(s["name"], len(ms), "frames", round(time.time() - t0, 1), "s", flush=True)
