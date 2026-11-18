import os, sys
os.environ["TLMOD"] = "tl8"; sys.argv = [sys.argv[0], "final"]
import render8 as R, fxcomp as X, fxtype as FT, numpy as np, cv2, math
from r2core import *
R.setup8(); FT.FD = R.ROOT + "/fonts3/"; FT._fc.clear()
def G(t, f, sz, tr=0): return FT.glyphs(t, f, sz, tracking=tr)
def box(c, x, y, lines, font, sz, fg, bg, bd, tr=0, lead=1.18, pad=(34, 24), slant=0.0):
    ms = [G(l, font, sz, tr) for l in lines]; capH = G("H", font, sz).shape[0]; w = max(m.shape[1] for m in ms); h = int(capH * lead * (len(ms) - 1) + capH)
    x0, y0, x1, y1 = int(x), int(y), int(x + w + 2 * pad[0]), int(y + h + 2 * pad[1])
    cv2.rectangle(c, (x0, y0), (x1, y1), bg, -1); cv2.rectangle(c, (x0, y0), (x1, y1), bd, 5, cv2.LINE_AA)
    for i, m in enumerate(ms):
        yy = y0 + pad[1] + int(i * capH * lead) + capH - m.shape[0] + int(m.shape[0] - capH) // 2 if False else y0 + pad[1] + int(i * capH * lead)
        roi = c[yy:yy + m.shape[0], x0 + pad[0]:x0 + pad[0] + m.shape[1]]; a = m[..., None].astype(np.float32) / 255
        roi[:] = (roi * (1 - a) + np.array(fg, np.float32) * a).astype(np.uint8)
    return c
page = R.intro_page(4.6); tiles = []
L = ["THE BODY THAT", "I’M IN RIGHT NOW,"]
for nm, kw in (("A ComicNeue BoldItalic / white box", dict(font="ComicNeue-BoldItalic.ttf", sz=64, fg=(12, 12, 14), bg=(240, 240, 238), bd=(12, 12, 14))),
               ("B Shantell XBold / white box", dict(font="ShantellSans-XBold.ttf", sz=58, fg=(12, 12, 14), bg=(240, 240, 238), bd=(12, 12, 14))),
               ("C Barlow SemiCond XBold / black box", dict(font="BarlowSemiCond-XBold.ttf", sz=62, fg=(240, 240, 238), bg=(10, 10, 12), bd=(240, 240, 238), tr=2)),
               ("D PatrickHand SC / white box", dict(font="PatrickHandSC.ttf", sz=72, fg=(12, 12, 14), bg=(240, 240, 238), bd=(12, 12, 14))),
               ("E Bangers / white box", dict(font="Bangers.ttf", sz=70, fg=(12, 12, 14), bg=(240, 240, 238), bd=(12, 12, 14), tr=3)),
               ("F Kanit XBold Italic / black box", dict(font="Kanit-ExtraBoldItalic.ttf", sz=58, fg=(240, 240, 238), bg=(10, 10, 12), bd=(240, 240, 238)))):
    c = page.copy(); box(c, 90, 560, L, **kw); cv2.putText(c, nm, (40, 1050), 0, 1.2, (0, 255, 255), 3); tiles.append(cv2.resize(c, (960, 540), interpolation=cv2.INTER_AREA))
cv2.imwrite("out/type_cap.jpg", np.vstack([np.hstack(tiles[i:i + 2]) for i in range(0, 6, 2)]), [cv2.IMWRITE_JPEG_QUALITY, 88])
# impact word on the FACE scene
H, W = R.H, R.W; tiles = []
def scene():
    canvas = R.tone_field((28, 18, 120), (8, 6, 30), 9.0, (0.05, 0.95), (0.7, 0.7)); return canvas
def skull(canvas):
    img, m = R.srcm("V2", 9.1, "duo_bone"); R.stick_full(canvas, img, m, px=0, shadow=(14, -18, 22, 0.7), dx=560, dy=20, rot=2)
def hard(mask, fill, sh=(10, 10, 12), d=14, ang=40):
    return FT.vrens(mask, fill=fill, depth=d / mask.shape[0], angle=ang, ext=sh, shadow=0)
for nm, mk in (("1 Anton flat + hard shadow", lambda: hard(FT.shear(G("FACE", R.ROOT + "/fonts/Anton.ttf", 520, 4), 0.12), (244, 244, 240))),
               ("2 Bangers + outline", lambda: layer(G("FACE", "Bangers.ttf", 520, 8), fill=(244, 244, 240), stroke=((10, 10, 12), 12), extrude=(16, 0.8, 0.8, (10, 10, 12)))),
               ("3 Saira XCond Black", lambda: hard(FT.shear(G("FACE", "SairaXCond-Black.ttf", 600, 2), 0.14), (244, 244, 240))),
               ("4 Kanit Black Italic", lambda: hard(G("FACE", "Kanit-BlackItalic.ttf", 470, -2), (244, 244, 240))),
               ("5 kanji + small latin", None),
               ("6 Archivo Black", lambda: hard(G("FACE", "ArchivoBlack.ttf", 430, -6), (244, 244, 240)))):
    c = scene()
    if mk is None:
        k = FT.flat(G("顔", "YujiBoku.ttf", 900), (244, 244, 240)); X.place(c, *k, 560, 540, 1.0, -4)
        s_ = FT.flat(G("FACE  TO  FACE", "BarlowSemiCond-XBold.ttf", 54, 14), (244, 244, 240)); X.place(c, *s_, 520, 1000)
    else:
        pm, a = mk(); X.place(c, pm, a, 560, 560, min(1.0, 1000 / a.shape[1]), -3)
    skull(c); cv2.putText(c, nm, (40, 1050), 0, 1.2, (0, 255, 255), 3); tiles.append(cv2.resize(c, (960, 540), interpolation=cv2.INTER_AREA))
cv2.imwrite("out/type_imp.jpg", np.vstack([np.hstack(tiles[i:i + 2]) for i in range(0, 6, 2)]), [cv2.IMWRITE_JPEG_QUALITY, 88])
