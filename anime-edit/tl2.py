"""V2 timeline: Dead Mount Death Play x 'Ain't No Mountain High Enough'.
Times are seconds on the output timeline. Presentation (cards, polaroids, film frame, text) lives in render2.py."""
import json, os

ROOT = os.path.dirname(os.path.abspath(__file__))
B = json.load(open(f"{ROOT}/audio/song_analysis.json"))["beats"]
SRC_FPS = 24000 / 1001
END = 39.3

DLG_OPEN_T = 0.30      # "All I wanted / was peace. / Nothing more."
DLG_MID_T = 28.52      # "I'll protect you, no matter what."
DLG_CLOSE_T = 33.85    # "It seems this land I've arrived in is peaceful."
CHORUS = 30.50
TITLE = dict(t0=5.86, zoom_start=7.10, t_full=7.76, t1=8.22)
END_TITLE = dict(t0=36.80, stamp=37.55, t1=END)

SHOTS = []
BY = {}


def S(name, t0, t1, ep, ss, speed=1.0, z=(1.06, 1.0), pan=None, rot=(0, 0), grade="battle", punch=0.0, mode="full",
      matte=False, impact=False, shake=0.0, fin=0.0, fout=0.0):
    s = dict(id=len(SHOTS), name=name, t0=t0, t1=t1, ep=ep, ss=ss, speed=speed, z=z, pan=pan or ((0.5, 0.5), (0.5, 0.5)), rot=rot,
             grade=grade, punch=punch, mode=mode, matte=matte, impact=impact, shake=shake, fin=fin, fout=fout, region=None)
    SHOTS.append(s); BY[name] = s


# A. cold open: old film reel (storybook past)
S("A1", 0.00, 2.02, 2, 3.4, z=(1.02, 1.12), grade="past", mode="film")
S("A2", 2.02, 3.92, 2, 64.7, z=(1.12, 1.03), grade="past", mode="film")
S("A3", 3.92, 5.86, 2, 21.9, z=(1.03, 1.18), pan=((0.5, 0.5), (0.50, 0.44)), grade="past", mode="film")
# B. title footage (inside the letters, then full frame)
S("B", 5.86, 8.22, 1, 1370.48, z=(1.0, 1.0), grade="raw", mode="title")       # OFFICIAL logo build: DEAD / MOUNT / DEATH / full
# C. verse — full-frame punches <-> floating bordered cards
S("C1", 8.22, 9.10, 1, 120.3, speed=[(0, 1.7), (0.45, 0.75), (1, 0.9)], z=(1.12, 1.03), grade="battle", punch=0.8, matte=True)
S("C2", 9.10, 10.08, 1, 154.15, speed=0.80, z=(1.02, 1.08), grade="battle", mode="card")
S("C3a", 10.08, 10.54, 1, 159.70, z=(1.12, 1.04), grade="battle", punch=0.7)
S("C3b", 10.54, 10.96, 1, 195.30, z=(1.04, 1.12), grade="battle", punch=0.7)
S("C4", 10.96, 11.98, 1, 514.25, z=(1.06, 1.02), grade="battle", mode="card")
S("C5a", 11.98, 12.30, 1, 250.2, z=(1.10, 1.04), grade="battle", punch=0.7)
S("C5b", 12.30, 12.59, 1, 210.0, z=(1.04, 1.12), grade="battle", punch=0.7)
S("C6a", 12.59, 13.26, 1, 205.25, z=(1.04, 1.04), grade="battle", mode="card")
S("C6b", 13.26, 13.89, 1, 216.62, z=(1.04, 1.04), grade="battle", mode="card")
S("C7a", 13.89, 14.37, 1, 506.5, z=(1.02, 1.12), grade="battle", punch=1.0, impact=True)
S("C7b", 14.37, 14.86, 1, 499.5, z=(1.12, 1.03), grade="battle", punch=0.9)
S("C8a", 14.86, 15.33, 1, 513.0, z=(1.03, 1.12), grade="battle", punch=0.9)
S("C8b", 15.33, 16.00, 1, 518.0, speed=1.8, z=(1.02, 1.30), grade="battle", punch=0.6)
# D. reincarnation -> Shinjuku
S("D1", 15.77, 16.67, 1, 531.0, z=(1.35, 1.04), rot=(-8, 4), grade="battle")
S("D2", 16.67, 17.65, 1, 594.2, z=(1.02, 1.10), grade="city")
S("D3", 17.65, 18.60, 1, 606.3, z=(1.16, 1.16), pan=((0.5, 0.56), (0.5, 0.44)), grade="city", punch=0.35)
S("D4", 18.60, 19.70, 1, 596.6, z=(1.14, 1.02), grade="city", punch=0.35)
S("D5L", 19.50, 21.34, 1, 381.4, z=(1.04, 1.10), grade="battle", mode="duo")
S("D5R", 19.50, 21.34, 1, 1265.7, z=(1.10, 1.04), grade="city", mode="duo")
# E. the people he answers to — polaroids, then the power wakes
S("E0", 21.34, 22.04, 1, 692.0, z=(1.02, 1.10), grade="night", punch=0.4)
S("PH1", 22.04, 25.80, 1, 678.6, z=(1.08, 1.08), grade="city", mode="photo")
S("PH2", 23.22, 25.80, 1, 760.2, z=(1.02, 1.02), grade="city", mode="photo", matte=True)
S("PH3", 24.15, 25.80, 1, 914.0, z=(1.06, 1.06), grade="night", mode="photo")
S("PH4", 25.10, 25.80, 1, 1275.2, z=(1.04, 1.04), grade="battle", mode="photo")
# the cafe: Lemmings (E04 reveal + E05 bar fight)
S("L1", 25.80, 26.47, 4, 1321.6, z=(1.04, 1.20), grade="night", punch=1.0)                 # Lemmings revealed
S("L2", 26.47, 26.91, 5, 91.62, z=(1.10, 1.02), grade="bar", punch=0.9)                    # bandaged fist catches the blow
S("L3", 26.91, 27.38, 5, 324.72, z=(1.03, 1.12), grade="bar", punch=0.8)                   # Misaki, caught
S("L4", 27.38, 27.84, 5, 112.90, z=(1.10, 1.02), grade="bar", punch=0.9)                   # Polka lunges
S("L5", 27.84, 28.31, 5, 341.10, speed=0.95, z=(1.03, 1.12), grade="night", punch=1.0)                 # the ghosts that haunt Lemmings
S("L6", 28.31, 28.55, 5, 297.95, z=(1.10, 1.03), grade="night", punch=0.9)                 # first circle
# P. pocket: "I'll protect you, no matter what."
S("P1", 28.55, 29.62, 5, 327.3, speed=0.9, z=(1.04, 1.10), grade="bar_hi", mode="card")       # Misaki in Lemmings' grip
S("P2", 29.62, 30.50, 5, 388.95, speed=0.75, z=(1.04, 1.22), grade="bar", mode="card")                 # Polka's eyes
# F. chorus = the spell in the bar
S("F1", 30.50, 30.96, 5, 394.72, z=(1.22, 1.06), grade="night", punch=1.4, impact=True, shake=0.6)   # energy burst
S("F2", 30.96, 31.44, 5, 397.2, z=(1.04, 1.18), grade="night", punch=1.2, impact=True, shake=0.6)    # circle array
S("F3", 31.44, 31.89, 5, 410.2, z=(1.18, 1.04), grade="bar", punch=1.2, impact=True, shake=0.6)      # giant skeleton rises in the bar
S("F4", 31.89, 32.44, 5, 131.55, z=(1.04, 1.16), grade="night", punch=1.4, impact=True, shake=0.6)   # the Corpse God's true form
S("F5a", 32.44, 32.64, 5, 403.0, z=(1.14, 1.04), grade="night", punch=1.0, shake=0.6)                # white burst
S("F5b", 32.64, 32.83, 5, 414.05, z=(1.04, 1.14), grade="bar", punch=1.0, shake=0.6)                 # red eyes
S("F6", 32.83, 33.95, 5, 405.95, z=(1.16, 1.04), grade="night", punch=1.4, impact=True, matte=True)  # Polka in the blue light
# G. outro
S("G1", 33.60, 36.25, 1, 682.9 - (DLG_CLOSE_T - 33.60), z=(1.03, 1.09), grade="city", fin=0.35, matte=True)
S("G2", 35.85, 39.3, 1, 1295.9, speed=1.40, z=(1.0, 1.0), grade="raw", mode="endlogo", fin=0.4)   # OFFICIAL title card (played backwards)


def letterbox(t):
    """bar height as a fraction of frame height (each bar)."""
    def lerp(a, b, u):
        u = max(0.0, min(1.0, u)); u = u * u * (3 - 2 * u); return a + (b - a) * u
    if t < 5.86: return 0.0            # film frame handles its own borders
    if t < 8.22: return 0.0
    if t < 15.40: return 0.094
    if t < 15.77: return lerp(0.094, 0.0, (t - 15.40) / 0.37)
    if t < 16.67: return 0.0
    if t < 17.0: return lerp(0.0, 0.094, (t - 16.67) / 0.33)
    if t < 22.04: return 0.094
    if t < 25.80: return 0.0            # polaroid table
    if t < 28.55: return 0.094
    if t < CHORUS: return 0.0           # pocket card on black
    if t < 33.30: return 0.0
    if t < 36.55: return lerp(0.0, 0.128, (t - 33.30) / 0.7)
    return lerp(0.128, 0.0, (t - 36.55) / 0.30)       # bars open for the logo
