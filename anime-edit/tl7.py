"""V7 timeline — the edit rebuilt around SYNTHETIC (song2/raw.wav, 123 BPM, ends 40.55).
Story: who is wearing Polka Shinoyama's face?  Intro identity file -> official logo -> verse of faces and masks ->
drop (four 3-3-2 bass cycles: past life, rebirth, the cafe, the spell) -> mirror outro -> Lisa's line in the silence -> end card."""
import json, os

ROOT = os.path.dirname(os.path.abspath(__file__))
B = json.load(open(f"{ROOT}/song2/analysis.json"))["beats"]
SRC_FPS = 24000 / 1001
SONG_END = 40.55
END = 47.40
CHORUS = 16.13                     # the drop
DROP_END = 31.46
TAG_T = 40.80                      # Lisa: "Whoever you are... at least not on the inside."
CARD_T = 45.20                     # official title card
DLG_OPEN_T, DLG_MID_T, DLG_CLOSE_T = 0.30, 99.0, 99.0      # (render2 compatibility)
LOGO_T = (6.11, 6.59, 7.06, 7.52, 8.03)
LOGO_PUSH = (7.78, 0.172, 0.505, 34.0)
BASS = [16.13, 16.85, 17.57, 18.30, 19.01, 19.96, 20.69, 21.41, 22.14, 22.86, 23.81, 24.53, 25.25, 25.97, 26.69, 27.65, 28.36, 29.08, 29.81, 30.78]
ACCENTS = [24.79, 26.70, 28.62, 30.55]
WHAT = [18.98, 19.54, 21.54, 22.36, 25.02, 27.34, 29.16, 29.72]
FLASHES = [(16.13, 0.20, 0.55), (24.79, 0.12, 0.45), (26.70, 0.12, 0.40), (28.62, 0.12, 0.45), (30.55, 0.18, 0.60), (19.96, 0.30, 0.5)]
TITLE = dict(t0=6.11, zoom_start=7.52, t_full=8.03, t1=8.03)
END_TITLE = dict(t0=CARD_T, stamp=CARD_T + 0.6, t1=END)
FLASH = []

SHOTS = []
BY = {}


def S(name, t0, t1, ep, ss, speed=1.0, z=(1.06, 1.0), pan=None, rot=(0, 0), grade="battle", punch=0.0, mode="full",
      matte=False, impact=False, shake=0.0, fin=0.0, fout=0.0, ink=None, ink_pct=58, rev=False, echo=0, mirror=False, par=None):
    s = dict(id=len(SHOTS), name=name, t0=t0, t1=t1, ep=ep, ss=ss, speed=speed, z=z, pan=pan or ((0.5, 0.5), (0.5, 0.5)), rot=rot,
             grade=grade, punch=punch, mode=mode, matte=matte, impact=impact, shake=shake, fin=fin, fout=fout, region=None,
             ink=ink, ink_pct=ink_pct, rev=rev, echo=echo, mirror=mirror)
    if par: s["par"] = par
    SHOTS.append(s); BY[name] = s


RAMP = [(0, 0.55), (0.55, 0.85), (1, 2.3)]
# ---------------- INTRO 0 - 6.11: the identity file
S("H1", 0.81, 2.74, 1, 688.24, speed=0.37, z=(1.0, 1.08), pan=((0.55, 0.45), (0.58, 0.40)), grade="city", mode="hud")      # his eye opens
S("H2", 2.74, 4.67, 1, 650.75, speed=1.0, z=(1.04, 1.10), grade="city", mode="hud")                                            # the hands of a stranger
S("H3", 4.67, 6.11, 1, 682.60, speed=0.9, z=(1.10, 1.02), grade="city", mode="hud")                                            # this body's face
# ---------------- LOGO 6.11 - 8.03
S("B", 6.11, 8.03, 1, 1370.48, z=(1.0, 1.0), grade="raw", mode="title")
# ---------------- VERSE 8.03 - 16.13  (FACE 8.74, FACE 9.46, unmasked 11.68, armageddon 12.78, tears 13.74, demons 15.20)
S("V1", 8.03, 8.74, 1, 154.16, speed=0.82, z=(1.0, 1.0), grade="battle", rev=True, mode="special")      # out of the skull's eye socket
S("V2", 8.74, 9.46, 1, 424.90, z=(1.04, 1.14), grade="battle", punch=0.6, ink="wb")                      # the old face
S("SKa", 9.46, 9.94, 5, 412.95, z=(1.0, 1.0), grade="bar", punch=0.8, mode="split")                       # face to face ...
S("SKb", 9.94, 10.43, 5, 414.05, z=(1.0, 1.0), grade="bar", punch=0.6, mode="split")
S("PF", 9.46, 10.43, 5, 342.15, speed=0.5, z=(1.0, 1.0), grade="bar", mode="split")
S("V4", 10.43, 11.38, 1, 120.3, speed=[(0, 1.7), (0.45, 0.75), (1, 0.9)], z=(1.12, 1.03), grade="battle", punch=0.8, matte=True, mode="inkcut")   # Shagrua, honour
S("V5a", 11.38, 11.68, 1, 761.05, z=(1.08, 1.02), grade="city", punch=0.5)                                # Misaki's smile ...
S("V5b", 11.68, 12.35, 1, 1029.6, z=(1.03, 1.12), grade="battle", punch=0.9, matte=True, mode="inkcut")   # ... unmasked
S("V6", 12.35, 13.28, 1, 381.4, z=(1.04, 1.16), grade="battle", punch=0.7)                                # armageddon
S("V7", 13.28, 14.26, 1, 1003.4, z=(1.08, 1.0), grade="night", punch=0.4)                                 # the dead children (tears)
S("V8", 14.26, 15.21, 1, 368.6, speed=RAMP, z=(1.24, 1.04), pan=((0.5, 0.40), (0.5, 0.52)), grade="battle", punch=0.8, ink="wb")   # father of demons
S("V9", 15.21, 16.13, 1, 1088.5, speed=1.7, z=(1.04, 1.22), pan=((0.5, 0.5), (0.62, 0.47)), grade="battle", punch=0.6)            # the eye turns
# ---------------- DROP 16.13 - 31.46
# cycle 1: the past life
S("D1", 16.13, 16.85, 1, 159.70, speed=RAMP, z=(1.14, 1.03), grade="battle", punch=1.2, impact=True, ink="wb")
S("D2", 16.85, 17.57, 1, 506.5, speed=RAMP, z=(1.02, 1.12), grade="battle", punch=1.0, impact=True, ink="wb")
S("D3", 17.57, 18.30, 1, 499.5, speed=RAMP, z=(1.12, 1.03), grade="battle", punch=0.9, ink="wb", echo=2)
S("D4", 18.30, 19.01, 1, 513.0, speed=RAMP, z=(1.03, 1.12), grade="battle", punch=0.9, ink="wb")
S("D5", 19.01, 19.96, 1, 216.62, z=(1.04, 1.10), grade="night", punch=0.8, echo=3)
# cycle 2: death and rebirth
S("D6", 19.96, 20.69, 1, 518.0, speed=1.8, z=(1.02, 1.30), grade="battle", punch=0.6)
S("R1", 20.40, 21.41, 1, 531.0, z=(1.22, 1.0), grade="battle")
S("R2", 21.10, 22.14, 1, 594.15, z=(1.0, 1.06), pan=((0.5, 0.5), (0.52, 0.46)), grade="city")
S("D9", 22.14, 22.86, 1, 1099.60, z=(1.0, 1.10), grade="ghost", punch=0.5)
S("D10", 22.86, 23.81, 1, 1107.40, z=(1.06, 1.0), grade="ghost", punch=0.4, matte=True, par=(0.07, 1.8))
# cycle 3: the cafe
S("L1", 23.81, 24.53, 4, 1321.6, z=(1.0, 1.30), grade="night", punch=1.0, ink="red", ink_pct=50)
S("L2", 24.53, 24.79, 5, 91.62, speed=RAMP, z=(1.10, 1.02), grade="bar", punch=0.9, ink="wb")
S("L3", 24.79, 25.25, 5, 324.72, z=(1.03, 1.10), grade="bar", punch=1.0)
S("L4", 25.25, 25.97, 5, 64.82, speed=RAMP, z=(1.03, 1.12), grade="bar", punch=0.9, ink="red", ink_pct=50)
S("L5", 25.97, 26.70, 5, 112.90, z=(1.10, 1.02), grade="bar", punch=1.0, ink="red", ink_pct=50)
S("L6", 26.70, 27.65, 5, 341.10, speed=0.45, z=(1.03, 1.14), grade="night", punch=1.2, impact=True)
# cycle 4: the spell
S("S1", 27.65, 28.36, 5, 394.72, speed=RAMP, z=(1.22, 1.06), grade="night", punch=1.2, shake=0.6, echo=2)
S("S2", 28.36, 28.62, 5, 397.2, z=(1.04, 1.18), grade="night", punch=1.0, shake=0.6, mirror=True)
S("S3", 28.62, 29.08, 5, 410.2, speed=RAMP, z=(1.18, 1.04), grade="bar", punch=1.4, impact=True, shake=0.6, ink="wb")
S("S4", 29.08, 29.81, 5, 131.55, z=(1.04, 1.16), grade="battle", punch=0.9, shake=0.6)
S("S5", 29.81, 30.55, 5, 414.05, z=(1.0, 1.12), grade="bar_hi", punch=1.0)
S("F6", 30.55, 31.46, 5, 405.95, z=(1.16, 1.04), grade="night", punch=1.4, impact=True, matte=True)
# ---------------- OUTRO 31.46 - 40.55  (mirror 33.04, recognize 34.46, myself 34.88, disappeared 36.52, mask 37.88, nothing 40.06)
S("O1a", 31.46, 33.46, 1, 594.20, speed=0.6, z=(1.0, 1.0), grade="city", mode="mirror")                  # Polka, profile
S("O1b", 31.46, 33.46, 1, 425.00, speed=0.6, z=(1.0, 1.0), grade="battle", mode="mirror")                # the skull, profile
S("O2", 33.46, 35.39, 1, 650.75, speed=0.9, z=(1.0, 1.10), grade="city", par=None)                       # the hands, again
S("O3", 35.39, 37.27, 1, 646.20, speed=0.8, z=(1.04, 1.12), grade="city")                                 # the real Polka, gone
S("O4", 37.27, 39.22, 2, 22.10, speed=0.95, z=(1.02, 1.12), grade="past")                                 # the mask
S("O5", 39.22, 40.80, 1, 683.40, speed=0.7, z=(1.04, 1.12), grade="city")                                 # nothing
# ---------------- TAG 40.80 - 45.20: Lisa's line in the silence; at "inside" the skull shows through his face
S("T1", 40.55, 45.20, 5, 342.15, speed=0.14, z=(1.0, 1.20), grade="bar")
# ---------------- END CARD
S("ST", 0.0, 0.81, 1, 1297.27, speed=0.25, z=(1.0, 1.0), grade="raw", mode="static")      # TV static before the file opens
S("G2", CARD_T, END, 1, 1296.0, speed=0.6, z=(1.0, 1.0), grade="raw", mode="endlogo")


def letterbox(t):
    def lerp(a, b, u):
        u = max(0.0, min(1.0, u)); u = u * u * (3 - 2 * u); return a + (b - a) * u
    if t < DROP_END: return 0.0
    if t < CARD_T - 0.1: return lerp(0.0, 0.11, (t - DROP_END) / 0.5)
    return 0.0
