"""V4 timeline — "one soul, two lives".
The official logo's black-and-white ink world carries through the edit: INK = death / the past life, COLOUR = life and magic.
No lyric text anywhere. Cuts sit on the musical beats. Scene logic lives in render4.py."""
import json, os

ROOT = os.path.dirname(os.path.abspath(__file__))
B = json.load(open(f"{ROOT}/audio/song_analysis.json"))["beats"]
SRC_FPS = 24000 / 1001
END = 39.3

DLG_OPEN_T = 0.30      # "All I wanted / was peace. / Nothing more."
DLG_MID_T = 28.52      # "I'll protect you, no matter what."
DLG_CLOSE_T = 33.85    # "It seems this land I've arrived in is peaceful."
CHORUS = 30.58
LOGO_PUSH = (7.84, 0.172, 0.505, 34.0)                     # dive into the "O" of MOUNT: (start, x, y, final zoom)
FLASHES = [(12.42, 0.14, 0.35), (21.80, 0.12, 0.45), (22.27, 0.14, 0.35), (25.54, 0.16, 0.50), (32.67, 0.10, 0.30)]

SHOTS = []
BY = {}


def S(name, t0, t1, ep, ss, speed=1.0, z=(1.06, 1.0), pan=None, rot=(0, 0), grade="battle", punch=0.0, mode="full",
      matte=False, impact=False, shake=0.0, fin=0.0, fout=0.0, ink=None, ink_pct=58, rev=False, echo=0, mirror=False):
    s = dict(id=len(SHOTS), name=name, t0=t0, t1=t1, ep=ep, ss=ss, speed=speed, z=z, pan=pan or ((0.5, 0.5), (0.5, 0.5)), rot=rot,
             grade=grade, punch=punch, mode=mode, matte=matte, impact=impact, shake=shake, fin=fin, fout=fout, region=None,
             ink=ink, ink_pct=ink_pct, rev=rev, echo=echo, mirror=mirror)
    SHOTS.append(s); BY[name] = s


# ---- cold open: old film reel (unchanged)
S("A1", 0.00, 2.02, 2, 3.4, z=(1.02, 1.12), grade="past", mode="film")
S("A2", 2.02, 3.92, 2, 64.7, z=(1.12, 1.03), grade="past", mode="film")
S("A3", 3.92, 5.86, 2, 21.9, z=(1.03, 1.18), pan=((0.5, 0.5), (0.50, 0.44)), grade="past", mode="film")
# v8: subliminal flash frames spliced into the reel (what is coming)
FLASH = [("X1", 1.51, 1, 154.60, "wb"), ("X2", 3.42, 1, 279.45, "red"), ("X3", 4.88, 5, 49.45, "wb")]
for _n, _t, _ep, _ss, _p in FLASH:
    S(_n, _t, _t + 0.05, _ep, _ss, z=(1.0, 1.0), grade="battle", ink=_p, ink_pct=55, mode="flash")
# ---- official logo build (unchanged), then the camera dives into its "O"
S("B", 5.86, 8.22, 1, 1370.48, z=(1.0, 1.0), grade="raw", mode="title")

# ================= I. THE PAST LIFE — ink, only the magic keeps its colour =================
S("I1", 8.22, 9.15, 1, 154.16, speed=0.82, z=(1.0, 1.0), grade="battle", rev=True, mode="special")        # v2: out of the giant skull's eye socket, no ink
S("I2", 9.15, 10.08, 1, 120.3, speed=[(0, 1.7), (0.45, 0.75), (1, 0.9)], z=(1.12, 1.03), grade="battle", punch=0.8, matte=True, mode="inkcut")
S("I3", 10.08, 10.54, 1, 159.70, speed=[(0, 0.55), (0.55, 0.85), (1, 2.3)], z=(1.12, 1.04), grade="battle", punch=0.7, ink="wb")
S("I4", 10.54, 11.03, 1, 208.70, speed=1.6, z=(1.10, 1.02), grade="battle", punch=0.7)                     # v2: golden shield circle -> beam
S("I5", 11.03, 11.98, 1, 368.6, speed=[(0, 0.55), (0.55, 0.85), (1, 2.3)], z=(1.24, 1.04), pan=((0.5, 0.40), (0.5, 0.52)), grade="battle", punch=1.0, ink="wb")
S("I6", 11.98, 12.50, 1, 279.3, z=(1.04, 1.16), pan=((0.5, 0.5), (0.49, 0.42)), grade="battle", punch=0.6, ink="wb")   # Shagrua's eye -> iris
S("I7a", 12.20, 12.91, 1, 205.0, z=(1.04, 1.04), grade="night", echo=3)                                # the dragon, in colour
S("I7b", 12.91, 13.42, 1, 216.62, z=(1.04, 1.08), grade="battle", punch=0.8, echo=3)
S("I8", 13.42, 13.89, 1, 506.5, speed=[(0, 0.55), (0.55, 0.85), (1, 2.3)], z=(1.02, 1.12), grade="battle", punch=1.0, impact=True, ink="wb")
S("I9", 13.89, 14.37, 1, 499.5, speed=[(0, 0.55), (0.55, 0.85), (1, 2.3)], z=(1.12, 1.03), grade="battle", punch=0.9, ink="wb", echo=2)
S("I10", 14.37, 14.86, 1, 513.0, speed=[(0, 0.55), (0.55, 0.85), (1, 2.3)], z=(1.03, 1.12), grade="battle", punch=0.9, ink="wb")
S("I11", 14.86, 15.33, 1, 514.25, z=(1.06, 1.02), grade="battle", punch=0.9)
S("I12", 15.33, 16.00, 1, 518.0, speed=1.8, z=(1.02, 1.30), grade="battle", punch=0.6)
# ================= II. REBIRTH — the reincarnation circle lands on his eye; this life is in colour =================
S("R1", 15.77, 16.98, 1, 531.0, z=(1.22, 1.0), grade="battle")
S("R2", 16.45, 17.65, 1, 594.15, z=(1.0, 1.06), pan=((0.5, 0.5), (0.52, 0.46)), grade="city")
S("R3", 17.65, 18.60, 1, 606.3, z=(1.16, 1.16), pan=((0.5, 0.56), (0.5, 0.44)), grade="city", punch=0.35)
S("R4", 18.60, 19.50, 1, 596.6, z=(1.14, 1.02), grade="city", punch=0.35)
# rhymes: past life (ink) | this life (colour)
S("Q1L", 19.50, 20.43, 2, 64.7, z=(1.04, 1.04), grade="past", mode="dip")           # the Corpse God among children
S("Q1R", 19.50, 20.43, 5, 1076.4, speed=0.9, z=(1.04, 1.04), grade="city", mode="dip")                    # Polka holding the twins
S("Q2L", 20.43, 21.34, 1, 381.4, z=(1.04, 1.04), grade="battle", ink="wb", mode="dip")                    # the battlefield burns
S("Q2R", 20.43, 21.34, 1, 1265.7, z=(1.04, 1.04), grade="city", mode="dip")                               # Shinjuku in the sun
# ================= III. THE EVIL EYE — he sees the dead; ink returns =================
S("E1", 21.34, 22.35, 5, 48.56, z=(1.02, 1.08), grade="night", mode="special")      # the show's own cut to the flaring eye lands on the beat (21.80)
S("E2", 22.05, 22.76, 1, 1099.60, z=(1.0, 1.10), grade="night")                                          # v3: the dead, glowing eyes on a red sky
S("E2b", 22.76, 23.22, 1, 1107.40, z=(1.06, 1.0), grade="night", punch=0.4, matte=True)
BY["E2b"]["par"] = (0.07, 1.8)                              # v3: Polka, standing before them
S("E3", 23.22, 23.68, 1, 761.05, z=(1.08, 1.02), grade="city", punch=0.5)                                  # Misaki, alive
S("E4", 23.68, 24.15, 1, 1029.6, z=(1.03, 1.12), grade="battle", punch=0.9, matte=True, mode="inkcut")    # Misaki, the killer
S("Q3T", 24.15, 25.10, 1, 279.4, z=(1.0, 1.0), grade="battle", ink="wb", mode="dip")                      # the hero who killed him
S("Q3B", 24.15, 25.10, 4, 1301.6, z=(1.0, 1.0), grade="night", ink="wb", mode="dip")                      # the monster who hunts him now
S("E6", 25.10, 25.54, 4, 1318.3, z=(1.04, 1.14), grade="night", punch=0.8, ink="red", ink_pct=50)
# ================= IV. THE CAFE — the Lemmings fight, in ink =================
S("L1", 25.54, 26.47, 4, 1321.6, z=(1.04, 1.20), grade="night", punch=1.0, ink="red", ink_pct=50)
S("L2", 26.47, 26.91, 5, 91.62, speed=[(0, 0.55), (0.55, 0.85), (1, 2.3)], z=(1.10, 1.02), grade="bar", punch=0.9, ink="wb")
S("L3", 26.91, 27.38, 5, 64.82, speed=[(0, 0.55), (0.55, 0.85), (1, 2.3)], z=(1.03, 1.12), grade="bar", punch=0.9, ink="red", ink_pct=50)
S("L4", 27.38, 27.84, 5, 324.72, z=(1.03, 1.10), grade="bar", punch=0.8)                    # Misaki stays in colour: she is alive
S("L5", 27.84, 28.31, 5, 112.90, speed=[(0, 0.55), (0.55, 0.85), (1, 2.3)], z=(1.10, 1.02), grade="bar", punch=1.0, ink="red", ink_pct=50)
S("L6", 28.31, 28.55, 5, 341.10, speed=0.95, z=(1.03, 1.10), grade="night", punch=1.0)
# the vow (dialogue)
S("P1", 28.55, 29.62, 5, 327.3, speed=0.9, z=(1.04, 1.10), grade="bar_hi", mode="card", ink="wb")
S("P2", 29.62, 30.58, 5, 388.95, speed=0.68, z=(1.04, 1.22), grade="bar", mode="card", ink="wb")
# ================= V. THE SPELL — colour floods back =================
S("S1", 30.58, 31.05, 5, 394.72, speed=[(0, 0.55), (0.55, 0.85), (1, 2.3)], z=(1.22, 1.06), grade="night", punch=1.4, impact=True, shake=0.6, echo=2)
S("S2", 31.05, 31.51, 5, 397.2, speed=[(0, 0.55), (0.55, 0.85), (1, 2.3)], z=(1.04, 1.18), grade="night", punch=1.2, shake=0.6, mirror=True)
S("S3", 31.51, 31.97, 5, 410.2, speed=[(0, 0.55), (0.55, 0.85), (1, 2.3)], z=(1.18, 1.04), grade="bar", punch=1.2, shake=0.6, ink="wb")
S("S4", 31.97, 32.44, 5, 131.55, z=(1.04, 1.16), grade="night", punch=1.4, impact=True, shake=0.6)
S("SKa", 32.44, 32.67, 5, 412.95, z=(1.0, 1.0), grade="bar", punch=1.0, mode="split")                     # the skull ...
S("SKb", 32.67, 32.90, 5, 414.05, z=(1.0, 1.0), grade="bar", punch=1.0, mode="split")                     # ... opens its eyes
S("PF", 32.44, 32.90, 5, 342.15, speed=0.5, z=(1.0, 1.0), grade="bar", mode="split")                                  # ... and the boy it lives in
S("F6", 32.90, 33.95, 5, 405.95, z=(1.16, 1.04), grade="night", punch=1.4, impact=True, matte=True)       # Polka, with the Corpse God behind him
# ---- outro (unchanged): Polka speaks, official title card played backwards
S("G1", 33.60, 36.25, 1, 682.9 - (DLG_CLOSE_T - 33.60), z=(1.03, 1.09), grade="city", fin=0.35, matte=True)
BY["G1"]["par"] = (0.06, 2.4)
S("G2", 35.45, 39.3, 1, 1295.9, speed=1.40, z=(1.0, 1.0), grade="raw", mode="endlogo", fin=0.4)


def letterbox(t):
    def lerp(a, b, u):
        u = max(0.0, min(1.0, u)); u = u * u * (3 - 2 * u); return a + (b - a) * u
    if t < 33.30: return 0.0
    if t < 36.55: return lerp(0.0, 0.128, (t - 33.30) / 0.7)
    return lerp(0.128, 0.0, (t - 36.55) / 0.30)
