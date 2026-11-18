"""V8 timeline = the tl7 story and sources (SYNTHETIC), re-cut for heavy compositing (render8).
Shots here are SOURCES: render8 decides how each one is cut out, inked, panelled and moved. Superset of tl7, so the older
scene code (logo, tag, end card) keeps working."""
from tl7 import *                    # B, SONG_END, END, CHORUS, DROP_END, TAG_T, CARD_T, LOGO_T, BASS, ACCENTS, WHAT, S(), SHOTS, BY ...
import tl7 as _t

FLASHES = [(16.13, 0.10, 0.45), (24.79, 0.06, 0.10), (28.62, 0.06, 0.16), (30.55, 0.08, 0.30)]
_t.FLASHES = FLASHES

# every shot that becomes a cut-out puppet needs a per-frame matte
for nm in ("H3", "PF", "V2", "V4", "V5b", "D2", "D3", "D10", "L1", "L5", "S4", "F6", "O1a", "O3", "O4", "R2"):
    BY[nm]["matte"] = True
for s in SHOTS: s["ink"] = None; s["punch"] = 0.0; s["impact"] = False; s["echo"] = 0; s["shake"] = 0.0; s["par"] = None if "par" in s else None

# extra sources for the composites
S("H1b", 0.81, 3.20, 1, 688.24, speed=0.30, z=(1.0, 1.05), grade="city")                      # the eye, for the first manga panel
S("SKe", 9.46, 10.43, 5, 414.05, speed=0.6, z=(1.0, 1.0), grade="bar", matte=False)           # red skull eye
S("CG", 28.62, 29.08, 5, 131.75, speed=0.6, z=(1.0, 1.0), grade="battle")                     # (spare) the corpse god behind Polka
S("D2b", 16.13, 16.85, 1, 506.90, speed=0.7, z=(1.0, 1.0), grade="battle", matte=True)        # the past-life Corpse God, screaming (cut-out)
S("W1", 23.81, 24.53, 4, 1321.6, speed=1.0, z=(1.0, 1.0), grade="night", matte=True)          # Lemmings, bandaged face (cut-out)
SEC = dict(intro=(0.0, 6.11), logo=(6.11, 8.03), verse=(8.03, 16.13), drop=(16.13, 31.46), outro=(31.46, 40.55), tag=(40.55, 45.20), card=(45.20, 47.40))
BY["D10"]["speed"] = 0.30                    # v21: hold on the frames where his figure separates cleanly from the crowd
