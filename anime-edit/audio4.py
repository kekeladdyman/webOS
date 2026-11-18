"""V4 soundtrack (re-timed to the V4 cut list)
V2 soundtrack: song + 3 dialogue lines + cinematic sound-effects layer (Mixkit library + two voice moments from the show)."""
import json, numpy as np, soundfile as sf, scipy.signal as sig, pyloudnorm as pyln, librosa
from scipy.ndimage import minimum_filter1d, uniform_filter1d
import tl4 as tl
SR = 48000; R = tl.ROOT; N = int(tl.END * SR)
rng = np.random.default_rng(3); meter = pyln.Meter(SR)
AN = json.load(open(f"{R}/sfx/analysis.json"))
def db(x): return 10 ** (x / 20)
def fade(x, a=0.02, b=0.05):
    x = x.copy(); na, nb = max(1, int(a * SR)), max(1, int(b * SR)); sh = (slice(None), None) if x.ndim > 1 else slice(None)
    x[:na] *= np.linspace(0, 1, na)[sh]; x[-nb:] *= np.linspace(1, 0, nb)[sh]; return x
def place(mix, x, t):
    i = int(round(t * SR))
    if x.ndim == 1: x = np.stack([x, x], 1)
    if i < 0: x = x[-i:]; i = 0
    j = min(len(mix), i + len(x))
    if j > i: mix[i:j] += x[:j - i]
def butter(x, fc, kind, order=4): return sig.sosfiltfilt(sig.butter(order, fc, kind, fs=SR, output="sos"), x, axis=0)
def reverb_ir(dur, decay, lp=5000):
    n = int(dur * SR); t = np.arange(n) / SR
    ir = rng.normal(0, 1, (n, 2)) * np.exp(-t / decay)[:, None]; ir = butter(ir, lp, "low", 2); ir[: int(0.004 * SR)] = 0
    return ir / np.sqrt((ir ** 2).sum(0)).mean()

# ------------------------------------------------------------ song
song, sr = sf.read(f"{R}/audio/song.wav", dtype="float32"); assert sr == SR
song = fade(song[: int(35.02 * SR)].astype(np.float64), 0.005, 0.03)
song *= db(-15.0 - meter.integrated_loudness(song[int(8 * SR): int(33 * SR)]))
music = np.zeros((N, 2)); place(music, song, 0.0)
lp = butter(music, 750, "low", 4) * db(-3.5)
env = np.zeros(N); a, b = int(28.34 * SR), int((tl.CHORUS - 0.02) * SR)
env[a:b] = 1.0; ra = int(0.22 * SR); env[a - ra:a] = np.linspace(0, 1, ra); rb = int(0.02 * SR); env[b:b + rb] = np.linspace(1, 0, rb)
music = music * (1 - env[:, None]) + lp * env[:, None]
duck = np.ones(N); o0, o1 = int((tl.DLG_OPEN_T - 0.1) * SR), int((tl.DLG_OPEN_T + 4.6) * SR)
duck[o0:o1] = db(-3.5); k = int(0.25 * SR); duck = np.convolve(duck, np.ones(k) / k, mode="same"); music *= duck[:, None]
tail_src = np.zeros((N, 2)); s0, s1 = int(32.6 * SR), int(35.02 * SR)
w = np.ones(s1 - s0); w[: int(0.6 * SR)] = np.linspace(0, 1, int(0.6 * SR)); tail_src[s0:s1] = music[s0:s1] * w[:, None]
wet = np.stack([sig.fftconvolve(tail_src[:, c], reverb_ir(4.5, 1.25, 3500)[:, c])[:N] for c in range(2)], 1)
music += wet * db(-9.0)

# ------------------------------------------------------------ dialogue
def stem(name, a, b):
    y, sr = sf.read(f"{R}/dlg/sep/htdemucs/{name}/vocals.wav", dtype="float32")
    return librosa.resample(y[int(a * sr): int(b * sr)].mean(1).astype(np.float64), orig_sr=sr, target_sr=SR)
def line(name, a, b, gate_db=-46):
    y = butter(stem(name, a, b), 85, "high", 2); w = int(0.02 * SR)
    e = np.sqrt(np.convolve(y ** 2, np.ones(w) / w, mode="same") + 1e-12)
    g = np.clip((20 * np.log10(e + 1e-9) - gate_db) / 10.0, 0.0, 1.0); g = np.convolve(g, np.ones(w) / w, mode="same")
    return fade(y * g, 0.03, 0.10)
def loud(y, target):
    yy = np.stack([y, y], 1) if y.ndim == 1 else y; pad = np.zeros((int(0.5 * SR), 2))
    L = meter.integrated_loudness(np.concatenate([pad, yy, yy, yy, pad]) if len(yy) < 1.5 * SR else yy)
    return y * db(target - L) if np.isfinite(L) else y
PRE = 0.14
segs = [("raw_peace", 4.24 - PRE, 5.50, tl.DLG_OPEN_T), ("raw_peace", 6.54 - PRE, 7.65, tl.DLG_OPEN_T + 1.95), ("raw_peace", 8.54 - PRE, 9.75, tl.DLG_OPEN_T + 3.60),
        ("raw_protect", 9.80 - PRE, 12.05, tl.DLG_MID_T), ("raw_land", 6.90 - PRE, 9.50, tl.DLG_CLOSE_T)]
dry = np.zeros((N, 2)); grp = {}
for nm, a, b, t in segs: grp.setdefault(nm, []).append((a, b, t))
for nm, items in grp.items():
    parts = [line(nm, a, b) for a, b, _ in items]; allp = loud(np.concatenate(parts), -15.2); k = 0
    for p, (_, _, t) in zip(parts, items):
        q = allp[k:k + len(p)]; k += len(p); place(dry, np.tanh(q * 1.15) / 1.15, t - PRE)
wetd = np.stack([sig.fftconvolve(dry[:, c], reverb_ir(2.2, 0.55, 6000)[:, c])[:N] for c in range(2)], 1)
dialog = dry + wetd * db(-15.0)

# ------------------------------------------------------------ sound effects
sfx = np.zeros((N, 2)); LOG = []
_cache = {}
def load(i):
    if i not in _cache:
        y, sr = sf.read(f"{R}/sfx/{i}.wav", dtype="float32", always_2d=True)
        if y.shape[1] == 1: y = np.repeat(y, 2, 1)
        y = y[:, :2].astype(np.float64)
        if sr != SR: y = np.stack([librosa.resample(y[:, c], orig_sr=sr, target_sr=SR) for c in range(2)], 1)
        _cache[i] = y
    return _cache[i]
def fx(i, t, lv, align="peak", maxd=None, fo=0.25, fi=0.004, pan=0.0, hp=None, lpf=None, start=0.0):
    """place library sound i so its peak/onset/start lands at t; lv = target loudness (LUFS-ish, music sits at -15)."""
    i = str(i); y = load(i); an = AN[i]
    off = {"peak": an["peak"], "on": an["on"], "start": 0.0}[align]
    g = db(lv - an["lufs"]) if np.isfinite(an["lufs"]) else 1.0
    y = y[int(start * SR):]
    if maxd: y = y[: int(maxd * SR)]
    pk = np.abs(y).max() * g; cap = db(lv + 10.5)                # sub-heavy sounds read low on a loudness meter: cap their peak too
    if pk > cap: g *= cap / pk
    y = y * g
    if maxd: y = y[: int(maxd * SR)]
    if hp: y = butter(y, hp, "high", 2)
    if lpf: y = butter(y, lpf, "low", 2)
    y = fade(y, fi, min(fo, len(y) / SR / 2))
    if pan: y = y * np.array([1 - max(0, pan), 1 + min(0, pan)])[None, :]
    place(sfx, y, t - off + start); LOG.append((round(t, 2), an["title"], lv))
def boom(t, f0=58, f1=30, dur=1.1, level=-9.0):
    n = int(dur * SR); tt = np.arange(n) / SR; f = f1 + (f0 - f1) * np.exp(-tt / 0.12)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.28); x[: int(0.004 * SR)] *= np.linspace(0, 1, int(0.004 * SR))
    place(sfx, fade(x * db(level), 0.001, 0.1), t)
def projector(t0, t1, level=-33.0):
    n = int((t1 - t0) * SR); tt = np.arange(n) / SR
    hum = butter(rng.normal(0, 1, n), [140, 900], "band", 2) * (0.6 + 0.4 * np.sin(2 * np.pi * 18 * tt)) * 0.5
    ticks = np.zeros(n); per = SR / 18.0; k = 0.0
    while k < n - 400:
        i = int(k + rng.normal(0, 30)); L = 260
        if 0 <= i < n - L: ticks[i:i + L] += rng.normal(0, 1, L) * np.exp(-np.arange(L) / 45.0)
        k += per
    ticks = butter(ticks, [900, 5200], "band", 2)
    crack = np.zeros(n)
    for i in rng.integers(0, n - 60, int((t1 - t0) * 22)): crack[i:i + 40] += rng.normal(0, 1, 40) * np.exp(-np.arange(40) / 9.0) * rng.uniform(0.3, 1.4)
    crack = butter(crack, 1800, "high", 2)
    x = hum * 0.9 + ticks * 0.8 + crack * 0.7; x = np.stack([x, np.roll(x, 37)], 1)
    x = loud(x, level); place(sfx, fade(x, 0.5, 0.05), t0)

C = tl.CHORUS
# -- cold open: old film + storybook pages
projector(0.0, 5.86); fx(1105, 2.02, -26); fx(1105, 3.92, -26); fx(1157, 3.5, -31, align="start", maxd=2.36, fi=1.2, fo=0.08)
fx(1349, 5.38, -27, align="start", maxd=0.5, fi=0.25, fo=0.05)
# -- title
# official logo build: DEAD (5.86) / MOUNT (6.32) / DEATH (6.78) / full logo (7.27)
fx(546, 5.86, -22, maxd=1.6, fo=0.7); fx(1031, 5.86, -26)
fx(2299, 6.32, -22); fx(1021, 6.32, -26)
fx(2299, 6.78, -21); fx(1031, 6.78, -26)
fx(2909, 7.27, -20, maxd=2.4, fo=1.1); fx(773, 7.27, -23, maxd=1.4, fo=0.7); boom(7.265, f0=64, f1=38, dur=0.7, level=-18.0)
fx(1492, 8.20, -23)
# -- the dive through the logo's "O" and out of the skull's eye socket
fx(1143, 8.24, -21, maxd=2.2, fo=1.0); fx(1466, 8.22, -24)
# -- I. the past life (ink)
fx(2798, 9.15, -21); fx(1472, 9.15, -25)
fx(1473, 10.08, -22); fx(1283, 10.56, -24, maxd=1.5, fo=0.7)
fx(779, 11.03, -22, maxd=1.8, fo=0.9); fx(2299, 11.52, -23)
fx(1464, 11.98, -25); fx(1492, 12.40, -22); fx(2303, 12.42, -23, maxd=0.9)
fx(167, 12.62, -22, maxd=1.6, fo=0.6); fx(1326, 12.91, -21)
fx(2789, 13.42, -21); fx(2166, 13.89, -21); fx(1476, 13.89, -24, maxd=1.0)
fx(775, 14.37, -21); fx(2794, 14.60, -23); fx(565, 14.86, -20, maxd=1.6, fo=0.8)
fx(2675, 15.77, -21, maxd=4.2, fo=1.8); fx(658, 15.80, -26, maxd=3.2, fo=1.4)
# -- II. rebirth: the circle lands on his eye, Shinjuku, the rhymes
fx(1471, 16.62, -23); fx(873, 16.90, -24)
fx(1471, 17.65, -23); fx(2301, 17.67, -21); fx(358, 17.45, -36, align="start", maxd=3.95, fi=0.6, fo=0.5)
fx(1469, 18.60, -24)
fx(3161, 19.50, -23); fx(1530, 19.50, -25); fx(1472, 20.43, -24); fx(1530, 20.43, -25)
# -- III. the Evil Eye
fx(2623, 22.27, -22, maxd=3.3, fo=0.5, start=1.2)
fx(1685, 21.80, -25, maxd=0.8); fx(2299, 21.80, -23)
fx(1492, 22.25, -22); fx(1340, 22.27, -22, maxd=1.2)
fx(1464, 23.22, -26); fx(2166, 23.68, -22); fx(2299, 23.68, -23)
fx(2301, 24.15, -22); fx(1021, 24.15, -27); fx(2301, 24.64, -22); fx(1031, 24.64, -27)
fx(773, 25.10, -23, maxd=1.2, fo=0.5)
# -- IV. the cafe: Lemmings
fx(1492, 25.52, -22); fx(773, 25.54, -21, maxd=1.5, fo=0.7); fx(2299, 25.54, -22)
fx(2655, 26.47, -20, maxd=0.7); fx(1472, 26.47, -25)
fx(1473, 26.91, -23); fx(2150, 26.93, -23)
fx(2150, 27.38, -22); fx(1464, 27.38, -26)
fx(1473, 27.84, -23); fx(2654, 27.86, -25, maxd=0.6)
fx(1340, 28.31, -22, maxd=0.9); fx(2303, 28.29, -22, maxd=0.9)
# -- the vow: heartbeat, riser, then the drop
fx(498, 28.70, -21, maxd=0.85, fo=0.3); fx(498, 29.60, -21, maxd=0.85, fo=0.3)
fx(788, C, -22, maxd=4.6, fo=1.6); fx(790, C - 0.02, -25)
fx(2782, C, -20, maxd=2.6, fo=1.4); boom(C - 0.005, level=-14.0)
# -- V. the spell
fx(1472, 31.05, -23); fx(2299, 31.05, -23); fx(1473, 31.51, -23); fx(2299, 31.51, -23)
fx(3057, 31.97, -21, maxd=1.4, fo=0.6); fx(1472, 32.44, -23); fx(2299, 32.44, -23); fx(773, 32.67, -22, maxd=1.0, fo=0.5)
fx(778, 32.90, -20, maxd=2.4, fo=1.2); fx(565, 32.90, -22, maxd=1.4)
# -- outro
fx(358, 33.9, -36, align="start", maxd=3.3, fi=0.8, fo=0.8)
# official title card: glitches in over the skyline, static, lands on white
fx(1457, 36.85, -28, align="start", maxd=0.6, fo=0.2); fx(1031, 37.12, -29); fx(1021, 37.42, -26)
fx(619, 37.55, -22, align="on", maxd=1.75, fo=0.9); fx(2299, 37.55, -24)
# -- voices from the show: Shagrua's battle cry, Misaki's laugh
v = fade(butter(stem("raw_scream", 0.55, 1.30), 120, "high", 2), 0.02, 0.12); place(sfx, loud(v, -21.0), 13.40)
v = fade(butter(stem("raw_laugh", 0.95, 2.35), 150, "high", 2), 0.03, 0.35); vv = np.stack([v, v], 1)
vv += np.stack([sig.fftconvolve(v, reverb_ir(1.6, 0.4, 5000)[:, c])[:len(v)] for c in range(2)], 1) * db(-12)
place(sfx, loud(vv, -24.0), 23.62)

# small duck of the music under the biggest hits so they read without getting louder
for t_, d_, amt in ((7.27, 0.5, -2.0), (C, 0.6, -2.0), (15.6, 0.7, -2.0)):
    i0, i1 = int(t_ * SR), int((t_ + d_) * SR); music[i0:i1] *= np.linspace(db(amt), 1.0, i1 - i0)[:, None]

sfx *= db(-2.0)                                                   # effects bus trim: support the song, don't fight it
mix = music + dialog + sfx
L = meter.integrated_loudness(mix[: int(36.0 * SR)]); mix *= db(-14.0 - L)
thr = db(-1.0); la = int(0.005 * SR); pk = np.abs(mix).max(1)
need = np.minimum(1.0, thr / np.maximum(pk, 1e-9)); g = uniform_filter1d(minimum_filter1d(need, size=2 * la + 1), size=la)
rel = np.empty_like(g); c = np.exp(-1 / (0.08 * SR)); acc = 1.0
for i in range(len(g)):
    acc = g[i] if g[i] < acc else 1 - (1 - acc) * c
    rel[i] = acc
mix *= rel[:, None]; mix = np.clip(mix, -thr, thr)
mix[-int(0.3 * SR):] *= np.linspace(1, 0, int(0.3 * SR))[:, None]
sf.write(f"{R}/out/mix4.wav", mix.astype(np.float32), SR)
np.save(f"{R}/out/stems4_dbg.npy", np.stack([music.mean(1), dialog.mean(1), sfx.mean(1)]).astype(np.float32))
for name, x in (("music", music), ("dialog", dialog), ("sfx", sfx)): print(name, "peak dBFS", round(20 * np.log10(np.abs(x).max() + 1e-9), 1))
print("mix LUFS", round(meter.integrated_loudness(mix[: int(36.0 * SR)]), 2), "| pre-norm", round(L, 2), "| limiter max GR dB", round(20 * np.log10(rel.min()), 2), "|", len(LOG), "library effects placed")
