"""contact sheet of a rendered video. usage: review.py video name t0 t1 step [cols] [tw]"""
import sys, cv2, numpy as np, os
v, name, t0, t1, step = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])
cols = int(sys.argv[6]) if len(sys.argv) > 6 else 8
tw = int(sys.argv[7]) if len(sys.argv) > 7 else 240
cap = cv2.VideoCapture(v); fps = cap.get(cv2.CAP_PROP_FPS); th = tw * 9 // 16
ts = list(np.arange(t0, t1 - 1e-6, step)); rows = (len(ts) + cols - 1) // cols
img = np.zeros((rows * th, cols * tw, 3), np.uint8)
for i, t in enumerate(ts):
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(t * fps))); ok, fr = cap.read()
    if not ok: continue
    fr = cv2.resize(fr, (tw, th), interpolation=cv2.INTER_AREA)
    cv2.putText(fr, f"{t:.2f}", (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(fr, f"{t:.2f}", (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 255), 1, cv2.LINE_AA)
    r, c = divmod(i, cols); img[r * th:(r + 1) * th, c * tw:(c + 1) * tw] = fr
out = f"{os.path.dirname(os.path.abspath(__file__))}/out/rev_{name}.jpg"; cv2.imwrite(out, img, [cv2.IMWRITE_JPEG_QUALITY, 85]); print(out, img.shape)
