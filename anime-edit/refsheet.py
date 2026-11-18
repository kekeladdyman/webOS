import sys, cv2, numpy as np
v, out, cols, rows, tw = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
t0 = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0; t1 = float(sys.argv[7]) if len(sys.argv) > 7 else None
cap = cv2.VideoCapture(v); fps = cap.get(cv2.CAP_PROP_FPS); n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
w, h = cap.get(3), cap.get(4); th = int(tw * h / w)
t1 = t1 or (n / fps - 3.0)
ts = np.linspace(t0, t1, cols * rows)
img = np.zeros((rows * th, cols * tw, 3), np.uint8)
for i, t in enumerate(ts):
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps)); ok, f = cap.read()
    if not ok: continue
    f = cv2.resize(f, (tw, th), interpolation=cv2.INTER_AREA)
    cv2.putText(f, f"{t:.1f}", (3, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 255, 255), 1, cv2.LINE_AA)
    r, c = divmod(i, cols); img[r * th:(r + 1) * th, c * tw:(c + 1) * tw] = f
cv2.imwrite(out, img, [cv2.IMWRITE_JPEG_QUALITY, 84]); print(out, img.shape)
