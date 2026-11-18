"""V7 soundtrack: SYNTHETIC + identity dialogue + effects.
V4 soundtrack (re-timed to the V4 cut list)
V2 soundtrack: song + 3 dialogue lines + cinematic sound-effects layer (Mixkit library + two voice moments from the show)."""
import json, numpy as np, soundfile as sf, scipy.signal as sig, pyloudnorm as pyln, librosa
from scipy.ndimage import minimum_filter1d, uniform_filter1d
import tl7 as tl
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

# ------------------------------------------------------------ song (SYNTHETIC, uninterrupted, ends 40.55)
song, sr = sf.read(f"{R}/song2/raw.wav", dtype="float32"); assert sr == SR
# v17: under the intro dialogue, dip only the song's vocal ad-libs (rebuilt from its stems; elsewhere the original mix is used untouched)
_st = {k: sf.read(f"{R}/song2/sep/htdemucs/raw/{k}.wav", dtype="float32")[0] for k in ("vocals", "drums", "bass", "other")}
_n = min(len(song), *(len(v) for v in _st.values())); vd = np.ones(_n)
for a_, b_ in ((0.20, 1.80), (2.45, 6.10)): vd[int(a_ * SR):int(b_ * SR)] = db(-16.0)
_k = int(0.08 * SR); vd = np.convolve(vd, np.ones(_k) / _k, mode="same")
_rebuilt = _st["vocals"][:_n] * vd[:, None] + _st["drums"][:_n] + _st["bass"][:_n] + _st["other"][:_n]
_sw = np.zeros(_n); _sw[: int(7.0 * SR)] = 1.0; _sw[int(7.0 * SR):int(7.2 * SR)] = np.linspace(1, 0, int(0.2 * SR))
song = song.copy(); song[:_n] = song[:_n] * (1 - _sw[:, None]) + _rebuilt * _sw[:, None]
song = fade(song[: int(tl.SONG_END * SR)].astype(np.float64), 0.005, 0.05)
song *= db(-15.0 - meter.integrated_loudness(song[int(8 * SR): int(31 * SR)]))
music = np.zeros((N, 2)); place(music, song, 0.0)
# dialogue duck in the intro (the song's soft ad-libs sit under the voices)
duck = np.ones(N)
for a_, b_, g_ in ((0.20, 1.85, -6.0), (2.45, 4.00, -9.0), (4.00, 6.10, -7.0)): duck[int(a_ * SR):int(b_ * SR)] = db(g_)
k = int(0.20 * SR); duck = np.convolve(duck, np.ones(k) / k, mode="same"); music *= duck[:, None]
# the song's last bar rings out under Lisa's line
tail_src = np.zeros((N, 2)); s0, s1 = int(38.6 * SR), int(tl.SONG_END * SR)
w = np.ones(s1 - s0); w[: int(0.8 * SR)] = np.linspace(0, 1, int(0.8 * SR)); tail_src[s0:s1] = music[s0:s1] * w[:, None]
wet = np.stack([sig.fftconvolve(tail_src[:, c], reverb_ir(6.0, 1.9, 2600)[:, c])[:N] for c in range(2)], 1)
music += wet * db(-10.0)

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
PRE = 0.12
segs = [("raw_body", 0.05 - 0.02, 1.52, 0.30),            # Misaki: "Can you say your own name?"
        ("raw_body", 9.535, 10.98, 2.62 + PRE),            # Polka: "The body that I'm in right now," (starts clean on "the")
        ("raw_body", 11.58 - PRE, 13.52, 4.06),           # "its name is... Polka Shinoyama."
        ("raw_inside2", 10.40 - PRE, 14.70, tl.TAG_T)]    # Lisa: "Whoever you are, it seems you're not Polka Shinoyama... at least not on the inside."
dry = np.zeros((N, 2)); grp = {}
for nm, a, b, t in segs: grp.setdefault(nm, []).append((a, b, t))
for nm, items in grp.items():
    parts = [line(nm, a, b) for a, b, _ in items]; allp = loud(np.concatenate(parts), -15.0); k = 0
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

def rfx(i, t_end, lv, dur=None):
    """reversed library sound whose (reversed) tail lands exactly at t_end: a suck-in swell."""
    i = str(i); y = load(i)[::-1].copy(); an = AN[i]
    g = db(lv - an["lufs"]) if np.isfinite(an["lufs"]) else 1.0; pk = np.abs(y).max() * g; cap = db(lv + 10.5)
    if pk > cap: g *= cap / pk
    y = y * g; end_i = int((an["dur"] - an["on"]) * SR); y = y[:min(len(y), end_i)]
    if dur: y = y[-int(dur * SR):]
    place(sfx, fade(y, 0.08, 0.004), t_end - len(y) / SR); LOG.append((round(t_end, 2), "rev " + an["title"], lv))
def whine(t0, t1, f=2900.0, lv=-34.0):
    n = int((t1 - t0) * SR); tt = np.arange(n) / SR
    x = (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(2 * np.pi * f * 2.01 * tt)) * np.clip(tt / ((t1 - t0) * 0.8), 0, 1) ** 2
    x = np.stack([x, np.roll(x, 23)], 1); x = loud(x, lv); x[-int(0.004 * SR):] *= np.linspace(1, 0, int(0.004 * SR))[:, None]
    place(sfx, x, t0)
C = tl.CHORUS
# -- intro: the identity file
fx(3120, 0.05, -27); fx(2951, 0.45, -28)
for _t in (0.81, 2.74, 4.67): fx(2948, _t, -25, maxd=0.5); fx(2299, _t, -26)              # cuts tear in like a bad signal
for _t in np.arange(0.30, 1.75, 0.075): fx(1061, float(_t), -36)                        # the question types itself
fx(2855, 5.12, -26); fx(1032, 5.62, -24, align="peak", maxd=0.9)                          # NAME found ... STATUS: DECEASED
# -- the official logo: DEAD / MOUNT / DEATH / full
fx(546, 6.11, -22, maxd=1.4, fo=0.6); fx(1031, 6.11, -26)
fx(2299, 6.59, -22); fx(1021, 6.59, -26); fx(2299, 7.06, -21); fx(1031, 7.06, -26)
fx(2909, 7.52, -21, maxd=2.0, fo=0.9); boom(7.515, f0=64, f1=38, dur=0.6, level=-19.0)
rfx(1492, 8.03, -23, dur=0.42); fx(1143, 8.05, -22, maxd=1.8, fo=0.9)
# -- verse
fx(1466, 8.74, -24); fx(2301, 9.46, -22); fx(1021, 9.94, -25)
fx(2798, 10.43, -21); fx(1472, 10.43, -25)
fx(1464, 11.38, -26); fx(2166, 11.68, -22); fx(2299, 11.68, -23)
fx(1328, 12.35, -23, maxd=1.4, fo=0.6); fx(779, 12.78, -23, maxd=1.4, fo=0.7)
fx(1157, 13.28, -31, align="start", maxd=1.0, fi=0.1, fo=0.4)
fx(1468, 14.26, -23); fx(2303, 14.72, -24, maxd=0.9)
fx(2629, 15.21, -24, maxd=1.0); whine(15.35, 15.95, lv=-34.0); rfx(1492, 16.13, -24, dur=0.30)
# -- the drop: a hit on every bass note, the four drum accents get the big ones
for _t in tl.BASS: fx(1472 if int(_t * 10) % 2 else 1473, _t, -26)
fx(788, C, -22, maxd=4.0, fo=1.6); fx(2782, C, -20, maxd=2.4, fo=1.2); boom(C - 0.005, level=-14.0)
fx(2789, 16.85, -22); fx(1506, 17.55, -24); fx(2166, 17.57, -22); fx(1506, 18.28, -24); fx(775, 18.30, -22)
fx(1328, 18.99, -22, maxd=1.4, fo=0.6); fx(2675, 19.96, -21, maxd=3.0, fo=1.4); fx(658, 20.0, -27, maxd=2.4, fo=1.2)
fx(873, 21.10, -23, align="start"); fx(2350, 21.95, -24, align="start", maxd=0.6, fo=0.2)
fx(1157, 22.14, -30, align="start", maxd=1.2, fi=0.1, fo=0.4); fx(2301, 22.86, -24)
for _b in [b for b in tl.B if 23.81 <= b < 24.53] + [(a + b) / 2 for a, b in zip(tl.B, tl.B[1:]) if 23.81 <= (a + b) / 2 < 24.53]:
    fx(1031 if int(_b * 100) % 2 else 1021, _b, -29)
fx(773, 23.81, -21, maxd=1.2, fo=0.6); fx(2655, 24.53, -21, maxd=0.7)
fx(677, 24.79, -20, maxd=1.6, fo=0.7); fx(1701, 24.85, -27, align="start", start=0.15, maxd=0.9, fo=0.5); boom(24.785, level=-17.0)
fx(1506, 25.24, -24); fx(2150, 25.25, -22); fx(1473, 25.97, -23); fx(2654, 25.99, -25, maxd=0.6)
fx(1347, 26.70, -22, maxd=1.2); fx(565, 26.70, -21, maxd=1.4, fo=0.7); boom(26.695, level=-18.0)
fx(2303, 27.65, -22, maxd=0.9); fx(2599, 27.65, -25, align="on", maxd=1.0, fo=0.5)
fx(1506, 28.60, -24); fx(3057, 28.62, -20, maxd=1.4, fo=0.6); boom(28.615, level=-17.0)
fx(1472, 29.08, -23); fx(773, 29.81, -22, maxd=1.0, fo=0.5)
fx(778, 30.55, -19, maxd=2.4, fo=1.2); fx(565, 30.55, -21, maxd=1.4); boom(30.545, level=-15.0)
# -- outro: the mirror
fx(2586, 31.50, -26, maxd=2.0, fo=0.8); fx(677, 32.20, -28, maxd=1.4, fo=0.7)
fx(2948, 34.46, -26, maxd=0.6); fx(1032, 34.88, -27, maxd=0.8)
fx(2350, 36.30, -24, maxd=1.6, fo=0.8); fx(1170, 36.10, -30, align="start", start=6.5, maxd=1.6, fi=0.3, fo=0.6)
fx(1468, 37.27, -24); fx(2630, 37.70, -27, maxd=1.8, fo=0.8)
fx(1157, 39.22, -32, align="start", maxd=1.8, fi=0.4, fo=0.8)
# -- tag + end card
fx(1177, 40.4, -36, align="start", start=8.0, maxd=4.8, fi=0.6, fo=0.8, hp=200)                # low wind under Lisa's line
fx(2630, 44.25, -31, maxd=0.9, fo=0.5, lpf=2500); fx(2299, 45.02, -23)                     # the skull shows through (kept under "inside")
fx(2948, CARD_T := tl.CARD_T, -24, maxd=0.5); fx(1457, tl.CARD_T, -28, align="start", maxd=0.35, fo=0.15)
boom(tl.CARD_T + 0.30, f0=60, f1=34, dur=0.9, level=-15.0); fx(619, tl.CARD_T + 0.30, -23, align="on", maxd=1.9, fo=1.0)

for t_, d_, amt in ((7.52, 0.5, -2.0), (C, 0.6, -2.0), (30.55, 0.6, -1.5)):
    i0, i1 = int(t_ * SR), int((t_ + d_) * SR); music[i0:i1] *= np.linspace(db(amt), 1.0, i1 - i0)[:, None]

gain = np.ones(N)                                                   # v17: SYNTHETIC is dense - lift the effects where the song is loudest
for a_, b_, g_ in ((8.03, 16.13, 3.0), (16.13, 31.46, 5.0)): gain[int(a_ * SR):int(b_ * SR)] = db(g_)
k = int(0.10 * SR); gain = np.convolve(gain, np.ones(k) / k, mode="same"); sfx *= gain[:, None]
lo = butter(sfx, 120, "low", 2); sfx = sfx - lo + lo * db(-4.5); sfx = butter(sfx, 32, "high", 2)   # v5: effects bus low shelf, no mud under the song
sfx *= db(-2.0)                                                   # effects bus trim: support the song, don't fight it
mix = music + dialog + sfx
L = meter.integrated_loudness(mix[: int(40.5 * SR)]); mix *= db(-14.0 - L)
thr = db(-1.0); la = int(0.005 * SR); pk = np.abs(mix).max(1)
need = np.minimum(1.0, thr / np.maximum(pk, 1e-9)); g = uniform_filter1d(minimum_filter1d(need, size=2 * la + 1), size=la)
rel = np.empty_like(g); c = np.exp(-1 / (0.08 * SR)); acc = 1.0
for i in range(len(g)):
    acc = g[i] if g[i] < acc else 1 - (1 - acc) * c
    rel[i] = acc
mix *= rel[:, None]; mix = np.clip(mix, -thr, thr)
mix[-int(0.3 * SR):] *= np.linspace(1, 0, int(0.3 * SR))[:, None]
sf.write(f"{R}/out/mix7.wav", mix.astype(np.float32), SR)
np.save(f"{R}/out/stems7_dbg.npy", np.stack([music.mean(1), dialog.mean(1), sfx.mean(1)]).astype(np.float32))
for name, x in (("music", music), ("dialog", dialog), ("sfx", sfx)): print(name, "peak dBFS", round(20 * np.log10(np.abs(x).max() + 1e-9), 1))
print("mix LUFS", round(meter.integrated_loudness(mix[: int(40.5 * SR)]), 2), "| pre-norm", round(L, 2), "| limiter max GR dB", round(20 * np.log10(rel.min()), 2), "|", len(LOG), "library effects placed")
