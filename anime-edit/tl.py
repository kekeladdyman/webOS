"""Timeline for the Dead Mount Death Play x 'Ain't No Mountain High Enough' edit.
All times are seconds on the output timeline. B[i] = detected beat i of the song."""
import json, os

ROOT = os.path.dirname(os.path.abspath(__file__))
B = json.load(open(f"{ROOT}/audio/song_analysis.json"))["beats"]
SRC_FPS = 24000 / 1001
END = 38.3

# ---- dialogue placement (output time of the first word) -------------------
DLG_OPEN_T = 0.30      # "All I wanted / was peace. / Nothing more."
DLG_MID_T = 28.52      # "I'll protect you, no matter what."
DLG_CLOSE_T = 33.85    # "It seems this land I've arrived in is peaceful."
CHORUS = 30.50         # "AIN'T no mountain high enough" slam

SHOTS = []


def S(t0, t1, ep, ss, speed=1.0, z=(1.06, 1.0), pan=None, rot=(0, 0), grade="battle", punch=0.0,
      fin=0.0, fout=0.0, region=None, tag="", shake=0.0, impact=False, sync=None):
    """t0,t1 output span | ep, ss source episode + start second | speed: float or [(u,speed),...]
    z=(zoom0,zoom1) | pan=((cx0,cy0),(cx1,cy1)) focus point in source | fin/fout cross-fade seconds
    region: split-screen rect spec | punch: cut accent strength | impact: 2-tone impact frames at cut"""
    SHOTS.append(dict(id=len(SHOTS), t0=t0, t1=t1, ep=ep, ss=ss, speed=speed, z=z,
                      pan=pan or ((0.5, 0.5), (0.5, 0.5)), rot=rot, grade=grade, punch=punch, fin=fin, fout=fout,
                      region=region, tag=tag, shake=shake, impact=impact))


# ---- A. cold open (storybook past) ---------------------------------------
S(0.00, 2.10, 2, 3.4, z=(1.04, 1.16), grade="past", fin=0.6, fout=0.35, tag="A1 child alone")
S(1.75, 4.05, 2, 64.7, z=(1.14, 1.03), grade="past", fin=0.35, fout=0.35, tag="A2 kids + hooded figure")
S(3.70, 5.86, 2, 21.9, z=(1.03, 1.20), pan=((0.5, 0.5), (0.52, 0.42)), grade="past", fin=0.35, tag="A3 skull reveal")
# ---- B. title: footage inside letters, zoom through ----------------------
S(5.86, 8.22, 1, 1279.3, z=(1.02, 1.10), grade="battle", tag="B title footage (skull demon)", shake=0.3)
# ---- C. verse: the other-world battle -------------------------------------
S(8.22, 9.10, 1, 120.9, z=(1.10, 1.02), grade="battle", punch=0.8, tag="C1 Shagrua sword")
S(9.10, 10.08, 1, 154.2, speed=0.82, z=(1.02, 1.10), grade="battle", punch=1.0, tag="C2 MOUNTAIN skeleton giant")
S(10.08, 10.54, 1, 159.75, z=(1.12, 1.04), grade="battle", punch=0.6, tag="C3a blue rings")
S(10.54, 10.98, 1, 195.3, z=(1.04, 1.12), grade="battle", punch=0.6, tag="C3b purple lightning")
S(10.98, 11.98, 1, 368.6, z=(1.30, 1.04), pan=((0.5, 0.40), (0.5, 0.52)), grade="battle", punch=1.0, tag="C4 VALLEY skeleton lord")
S(11.98, 12.30, 1, 250.2, z=(1.10, 1.04), grade="battle", punch=0.6, tag="C5a gold figure")
S(12.30, 12.62, 1, 209.6, z=(1.04, 1.12), grade="battle", punch=0.6, tag="C5b beam fire")
S(12.62, 13.89, 1, 204.3, z=(1.14, 1.14), pan=((0.44, 0.5), (0.56, 0.5)), grade="battle", punch=1.0, tag="C6 RIVER blue dragon")
S(13.89, 14.37, 1, 506.5, z=(1.02, 1.12), grade="battle", punch=1.0, tag="C7a Shagrua scream", impact=True)
S(14.37, 14.86, 1, 499.6, z=(1.12, 1.03), grade="battle", punch=0.8, tag="C7b gold slash")
S(14.86, 15.33, 1, 513.1, z=(1.03, 1.12), grade="battle", punch=0.8, tag="C8a sword strike")
S(15.33, 16.00, 1, 518.0, speed=1.8, z=(1.02, 1.30), grade="battle", punch=0.6, tag="C8b light pillar")
# ---- D. reincarnation -> Shinjuku ------------------------------------------
S(15.77, 16.67, 1, 531.0, z=(1.35, 1.04), rot=(-8, 4), grade="battle", tag="D1 reincarnation circle")
S(16.67, 17.65, 1, 594.2, z=(1.02, 1.10), grade="city", tag="D2 Polka reborn CU")
S(17.65, 18.60, 1, 606.3, z=(1.16, 1.16), pan=((0.5, 0.56), (0.5, 0.44)), grade="city", punch=0.35, tag="D3 Cocoon tower")
S(18.60, 19.86, 1, 596.6, z=(1.14, 1.02), grade="city", punch=0.35, tag="D4 Shinjuku street")
S(19.50, 21.34, 1, 381.4, z=(1.5, 1.5), pan=((0.40, 0.55), (0.60, 0.55)), grade="battle", region="L", tag="D5L other world in flames")
S(19.50, 21.34, 1, 1265.7, z=(1.5, 1.5), pan=((0.62, 0.5), (0.42, 0.5)), grade="city", region="R", tag="D5R Shinjuku skyline")
# ---- E. the people he answers to -------------------------------------------
S(21.34, 22.04, 1, 692.0, z=(1.02, 1.10), grade="night", punch=0.4, tag="E1 blue silhouette")
S(22.04, 22.76, 1, 678.6, z=(1.06, 1.14), grade="city", punch=0.3, tag="E2a little girl")
S(22.76, 23.22, 1, 1004.0, z=(1.12, 1.04), grade="night", punch=0.3, tag="E2b child spirits")
S(23.22, 24.01, 1, 760.3, z=(1.08, 1.02), grade="city", punch=0.5, tag="E3 Misaki smile")
S(24.01, 25.10, 1, 1029.6, z=(1.03, 1.14), grade="battle", punch=0.8, tag="E4 Misaki laugh")
S(25.10, 25.54, 1, 979.6, speed=1.3, z=(1.10, 1.03), grade="night", punch=0.7, tag="E5a Misaki lunge")
S(25.54, 26.03, 1, 958.4, z=(1.03, 1.10), grade="night", punch=0.7, tag="E5b knives")
S(26.03, 26.91, 1, 1088.5, speed=1.2, z=(1.04, 1.22), grade="battle", punch=0.8, tag="E6 eye ignites")
S(26.91, 27.84, 1, 1145.3, speed=1.4, z=(1.10, 1.02), grade="battle", punch=0.9, tag="E7 hand + tendrils")
S(27.84, 28.31, 1, 1149.3, speed=1.5, z=(1.03, 1.12), grade="battle", punch=0.8, tag="E8a circle forms")
S(28.31, 28.55, 1, 1155.9, speed=1.5, z=(1.10, 1.03), grade="battle", punch=0.9, tag="E8b rune flash")
# ---- P. pocket: "I'll protect you, no matter what." ------------------------
S(28.55, 29.62, 5, 1076.4, speed=0.9, z=(1.04, 1.13), grade="city", tag="P1 twins hug")
S(29.62, 30.50, 12, 1126.0, z=(1.04, 1.30), pan=((0.5, 0.5), (0.44, 0.47)), grade="night", tag="P2 half-skull face")
# ---- F. chorus --------------------------------------------------------------
S(30.50, 30.96, 12, 1189.7, z=(1.22, 1.06), grade="night", punch=1.4, impact=True, shake=0.6, tag="F1 hero circles AIN'T")
S(30.96, 31.44, 12, 1054.4, speed=1.5, z=(1.04, 1.18), grade="night", punch=1.2, impact=True, shake=0.6, tag="F2 sphere burst NO")
S(31.44, 31.89, 12, 1169.6, speed=1.5, z=(1.18, 1.04), grade="night", punch=1.2, impact=True, shake=0.6, tag="F3 spectral hands MOUNTAIN")
S(31.89, 32.44, 1, 459.25, z=(1.04, 1.16), grade="battle", punch=1.4, impact=True, shake=0.6, tag="F4 rainbow burst HIGH")
S(32.44, 32.83, 12, 551.0, z=(1.16, 1.04), grade="battle", punch=1.2, impact=True, shake=0.6, tag="F5 skull demon")
S(32.83, 33.95, 1, 1392.8, z=(1.30, 1.06), grade="battle", punch=1.4, impact=True, fout=0.35, tag="F6 hero CU ENOUGH")
# ---- G. outro ----------------------------------------------------------------
S(33.60, 36.25, 1, 682.9 - (DLG_CLOSE_T - 33.60), z=(1.03, 1.10), grade="city", fin=0.35, fout=0.4, tag="G1 Polka speaks (lip-sync)")
S(35.85, 37.05, 1, 1265.9, z=(1.10, 1.03), grade="city", fin=0.4, fout=0.5, tag="G2 peaceful skyline")

# ---- dialogue captions: (text, [(word, time offset from line start)], line start, line end) ----
CAPTIONS = [
    dict(t=DLG_OPEN_T, words=[("All", 0.00), ("I", 0.20), ("wanted", 0.36)], end=DLG_OPEN_T + 1.75),
    dict(t=DLG_OPEN_T + 1.95, words=[("was", 0.00), ("peace.", 0.22)], end=DLG_OPEN_T + 3.45),
    dict(t=DLG_OPEN_T + 3.60, words=[("Nothing", 0.00), ("more.", 0.30)], end=DLG_OPEN_T + 5.0),
    dict(t=DLG_MID_T, words=[("I’ll", 0.00), ("protect", 0.50), ("you,", 0.78), ("no", 1.06), ("matter", 1.18), ("what.", 1.44)],
         end=DLG_MID_T + 1.98, hard_end=CHORUS),
    dict(t=DLG_CLOSE_T, words=[("It", 0.00), ("seems", 0.12), ("this", 0.40), ("land", 0.64), ("I’ve", 0.90), ("arrived", 1.12),
                               ("in", 1.36), ("is", 1.58), ("peaceful.", 1.72)], end=DLG_CLOSE_T + 2.9),
]

# ---- big lyric words (difference blend) ------------------------------------------------
# kind: tall / low / wide / slam ; t0 = vocal onset
LYRICS = [
    dict(text="MOUNTAIN", t0=9.10, t1=10.08, kind="tall", hold=0.48, small=("ain’t no", 8.59), after=("high", 9.58)),
    dict(text="VALLEY", t0=10.96, t1=11.98, kind="low", hold=0.54, small=("ain’t no", 10.48), after=("low", 11.50)),
    dict(text="RIVER", t0=12.62, t1=13.89, kind="wide", hold=0.64, small=("ain’t no", 12.10), after=("wide", 13.26)),
    dict(text="ENOUGH", t0=14.08, t1=14.86, kind="slam", hold=0.29),
    dict(text="AIN’T", t0=30.50, t1=30.96, kind="slam"),
    dict(text="NO", t0=30.96, t1=31.44, kind="slam"),
    dict(text="MOUNTAIN", t0=31.44, t1=31.89, kind="slam"),
    dict(text="HIGH", t0=31.89, t1=32.44, kind="tall2"),
    dict(text="ENOUGH", t0=32.83, t1=33.60, kind="slam"),
]

# small italic lyric lines (lower third, subtle)
SMALL_LINES = [
    dict(text="if you need me, call me", t0=15.95, t1=17.55),
    dict(text="no matter where you are", t0=18.20, t1=19.45),
    dict(text="no matter how far", t0=20.10, t1=21.30, center=True),
    dict(text="don’t worry, baby", t0=22.04, t1=23.15),
    dict(text="just call my name", t0=23.95, t1=25.05),
    dict(text="i’ll be there in a hurry", t0=25.45, t1=26.85),
    dict(text="you don’t have to worry", t0=27.45, t1=28.50),
]

TITLE = dict(t0=5.86, zoom_start=7.10, t_full=7.76, t1=8.22)
END_TITLE = dict(t0=36.75, t1=END)


def letterbox(t):
    """bar height as a fraction of frame height (each bar)."""
    def lerp(a, b, u):
        u = max(0.0, min(1.0, u)); u = u * u * (3 - 2 * u); return a + (b - a) * u
    if t < 5.86: return 0.128
    if t < 8.22: return 0.0
    if t < 28.40: return 0.096
    if t < CHORUS: return lerp(0.096, 0.150, (t - 28.40) / 1.6)
    if t < 33.30: return 0.0
    return lerp(0.0, 0.128, (t - 33.30) / 0.7)
