"""re-render single 1-second chunks of the final: python rechunk9.py final 39 [41 ...]"""
import os, sys
os.environ["TLMOD"] = "tl9"
idx = [int(x) for x in sys.argv[2:]]; sys.argv = sys.argv[:2]
import render9 as R
R.setup9()
for i in idx:
    n0 = i * R.FPS; n1 = min(int(round(R.tl.END * R.FPS)), n0 + R.FPS); print(R.worker((i, n0, n1)), flush=True)
