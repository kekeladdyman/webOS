"""Contact sheets of shot mid-frames. usage: make_sheets.py EP [mode] ; mode=all|top"""
import sys, json, os
import cv2, numpy as np

root = os.path.dirname(os.path.abspath(__file__))
ep = sys.argv[1]
mode = sys.argv[2] if len(sys.argv) > 2 else "all"
topn = int(sys.argv[3]) if len(sys.argv) > 3 else 108
d = json.load(open(f"{root}/shots/ep{ep}.json"))
shots = [s for s in d["shots"] if s["dur"] >= 0.4 and s["luma"] > 12]
if mode == "top":
    # action score: motion * activity, favour shots 0.5-4s
    for s in shots:
        s["score"] = s["mot"] * (0.4 + s["act"]) + 0.04 * s["sat"]
    keep = sorted(shots, key=lambda s: -s["score"])[:topn]
    shots = sorted(keep, key=lambda s: s["i"])
TW, TH, LH, COLS, ROWS = 160, 90, 13, 12, 9
per = COLS * ROWS
os.makedirs(f"{root}/sheets", exist_ok=True)
for p in range(0, len(shots), per):
    chunk = shots[p:p + per]
    rows = (len(chunk) + COLS - 1) // COLS
    img = np.zeros((rows * (TH + LH), COLS * TW, 3), np.uint8)
    for j, s in enumerate(chunk):
        r, c = divmod(j, COLS)
        th = cv2.imread(f"{root}/shots/ep{ep}/{s['i']:04d}.jpg")
        if th is None:
            continue
        th = cv2.resize(th, (TW, TH), interpolation=cv2.INTER_AREA)
        y, x = r * (TH + LH), c * TW
        img[y:y + TH, x:x + TW] = th
        m, sec = divmod(int(s["t0"]), 60)
        col = (120, 255, 120) if s["mot"] > 6 else (255, 255, 255)
        cv2.putText(img, f"{s['i']} {m}:{sec:02d} {s['dur']:.1f}s", (x + 2, y + TH + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.36, col, 1, cv2.LINE_AA)
    out = f"{root}/sheets/ep{ep}_{mode}_{p // per:02d}.jpg"
    cv2.imwrite(out, img, [cv2.IMWRITE_JPEG_QUALITY, 80])
    print(out, len(chunk), f"shots {chunk[0]['i']}-{chunk[-1]['i']}")
