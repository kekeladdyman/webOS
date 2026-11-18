"""V9 timeline: same story and sources as tl8, cut as manga pages with a moving camera (render9)."""
from tl8 import *
import tl8 as _t8, tl7 as _t7

FLASHES = [(16.13, 0.10, 0.30), (30.55, 0.08, 0.18)]
_t7.FLASHES = FLASHES; _t8.FLASHES = FLASHES
# verified against the vocal stem (large-v3 + energy onsets)
LYR = dict(tears=13.38, demons=14.86, asking=15.38, what=15.99,
           mirror=[(32.24, "STRAIGHT"), (32.52, "IN"), (32.70, "THE"), (32.78, "MIRROR.")],
           recog=[(33.62, "I"), (33.74, "DON’T"), (34.04, "EVEN"), (34.14, "RECOGNIZE"), (34.56, "MYSELF.")],
           gone=[(35.16, "I"), (35.82, "FEEL"), (36.04, "LIKE"), (36.20, "I"), (36.26, "DISAPPEARED.")],
           mask=[(36.68, "I"), (37.06, "PUT"), (37.24, "ON"), (37.44, "A"), (37.62, "MASK.")])
