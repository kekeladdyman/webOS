"""Build the soundtrack: song (TikTok outro removed, normalised) + 3 isolated dialogue lines + minimal sound design."""
import numpy as np, soundfile as sf, scipy.signal as sig, pyloudnorm as pyln, librosa
import tl
SR = 48000; R = tl.ROOT
N = int(tl.END * SR)
rng = np.random.default_rng(3)
def db(x): return 10 ** (x / 20)
def fade(x, a=0.02, b=0.05):
    x = x.copy(); na, nb = int(a * SR), int(b * SR)
    x[:na] *= np.linspace(0, 1, na)[:, None] if x.ndim > 1 else np.linspace(0, 1, na)
    x[-nb:] *= np.linspace(1, 0, nb)[:, None] if x.ndim > 1 else np.linspace(1, 0, nb)
    return x
def place(mix, x, t):
    i = int(round(t * SR)); j = min(len(mix), i + len(x))
    if x.ndim == 1: x = np.stack([x, x], 1)
    mix[i:j] += x[:j - i]
def butter(x, fc, kind, order=4):
    sos = sig.butter(order, fc, kind, fs=SR, output="sos"); return sig.sosfiltfilt(sos, x, axis=0)
def reverb_ir(dur, decay, lp=5000):
    n = int(dur * SR); t = np.arange(n) / SR
    ir = rng.normal(0, 1, (n, 2)) * np.exp(-t / decay)[:, None]; ir = butter(ir, lp, "low", 2); ir[: int(0.004 * SR)] = 0
    return ir / np.sqrt((ir ** 2).sum(0)).mean()

meter = pyln.Meter(SR)
# ---------------- song ----------------
song, sr = sf.read(f"{R}/audio/song.wav", dtype="float32"); assert sr == SR
song = song[: int(35.02 * SR)].astype(np.float64); song = fade(song, 0.005, 0.03)
song *= db(-15.0 - meter.integrated_loudness(song[int(8 * SR): int(33 * SR)]))        # verse/chorus at -15 LUFS
music = np.zeros((N, 2)); place(music, song, 0.0)
# pocket before the chorus: muffle + duck the song under "I'll protect you, no matter what."
lp = butter(music, 750, "low", 4) * db(-3.5)
env = np.zeros(N); a, b = int(28.34 * SR), int((tl.CHORUS - 0.02) * SR)
env[a:b] = 1.0; ra = int(0.22 * SR); env[a - ra:a] = np.linspace(0, 1, ra); rb = int(0.02 * SR); env[b:b + rb] = np.linspace(1, 0, rb)
music = music * (1 - env[:, None]) + lp * env[:, None]
# gentle duck under the opening line (the intro groove is already quiet)
duck = np.ones(N); o0, o1 = int((tl.DLG_OPEN_T - 0.1) * SR), int((tl.DLG_OPEN_T + 4.6) * SR)
duck[o0:o1] = db(-3.5); k = int(0.25 * SR); duck = np.convolve(duck, np.ones(k) / k, mode="same"); music *= duck[:, None]
# reverb tail so the ending does not fall into dead silence when the song's own fade ends
tail_src = np.zeros((N, 2)); s0, s1 = int(32.6 * SR), int(35.02 * SR)
w = np.ones(s1 - s0); w[: int(0.6 * SR)] = np.linspace(0, 1, int(0.6 * SR)); tail_src[s0:s1] = music[s0:s1] * w[:, None]
wet = np.stack([sig.fftconvolve(tail_src[:, c], reverb_ir(4.5, 1.25, 3500)[:, c])[:N] for c in range(2)], 1)
music += wet * db(-9.0)

# ---------------- dialogue ----------------
def line(stem, a, b, gate_db=-46):
    y, sr = sf.read(f"{R}/dlg/sep/htdemucs/{stem}/vocals.wav", dtype="float32")
    y = y[int(a * sr): int(b * sr)].mean(1).astype(np.float64)
    y = librosa.resample(y, orig_sr=sr, target_sr=SR)
    y = butter(y, 85, "high", 2)
    # soft downward expander to remove separation residue between words
    w = int(0.02 * SR); e = np.sqrt(np.convolve(y ** 2, np.ones(w) / w, mode="same") + 1e-12)
    e = np.maximum.accumulate(e[::-1] * 0 + e) * 0 + e
    g = np.clip((20 * np.log10(e + 1e-9) - gate_db) / 10.0, 0.0, 1.0); g = np.convolve(g, np.ones(w) / w, mode="same")
    return fade(y * g, 0.03, 0.10)
def speech_gain(y, target=-15.2):
    yy = np.stack([y, y], 1); pad = np.zeros((int(0.5 * SR), 2))
    L = meter.integrated_loudness(np.concatenate([pad, yy, yy, yy, pad]) if len(yy) < 1.5 * SR else yy)
    return y * db(target - L)
PRE = 0.14
segs = [  # stem, start, end (seconds in stem file), output time of first word
    ("raw_peace", 4.24 - PRE, 5.50, tl.DLG_OPEN_T),            # "All I wanted"
    ("raw_peace", 6.54 - PRE, 7.65, tl.DLG_OPEN_T + 1.95),     # "was peace."
    ("raw_peace", 8.54 - PRE, 9.75, tl.DLG_OPEN_T + 3.60),     # "Nothing more."
    ("raw_protect", 9.80 - PRE, 12.05, tl.DLG_MID_T),          # "I'll protect you, no matter what."
    ("raw_land", 6.90 - PRE, 9.50, tl.DLG_CLOSE_T),            # "It seems this land I've arrived in is peaceful."
]
dry = np.zeros((N, 2)); grp = {}
for stem, a, b, t in segs: grp.setdefault(stem, []).append((a, b, t))
for stem, items in grp.items():
    parts = [line(stem, a, b) for a, b, _ in items]
    allp = speech_gain(np.concatenate(parts)); k = 0
    for p, (_, _, t) in zip(parts, items):
        q = allp[k:k + len(p)]; k += len(p); place(dry, np.tanh(q * 1.15) / 1.15, t - PRE)
wetd = np.stack([sig.fftconvolve(dry[:, c], reverb_ir(2.2, 0.55, 6000)[:, c])[:N] for c in range(2)], 1)
dialog = dry + wetd * db(-15.0)

# ---------------- minimal sound design ----------------
sfx = np.zeros((N, 2))
def boom(t, f0=58, f1=30, dur=1.1, level=-9.0):
    n = int(dur * SR); tt = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-tt / 0.12); ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-tt / 0.28); x[: int(0.004 * SR)] *= np.linspace(0, 1, int(0.004 * SR))
    place(sfx, fade(x * db(level), 0.001, 0.1), t)
def riser(t0, t1, level=-21.0):
    n = int((t1 - t0) * SR); u = np.arange(n) / n
    x = rng.normal(0, 1, n); out = np.zeros(n); nb = 24
    for i in range(nb):                                   # swept band-pass in blocks
        a, b = i * n // nb, (i + 1) * n // nb + 2048
        fc = 350 * (16 ** ((i + 0.5) / nb)); sos = sig.butter(2, [fc * 0.7, min(fc * 1.4, 20000)], "band", fs=SR, output="sos")
        seg = sig.sosfilt(sos, x[a:min(n, b)]); wdw = np.hanning(len(seg)); out[a:a + len(seg)] += seg * wdw
    out *= u ** 2.2; out /= np.abs(out).max() + 1e-9
    place(sfx, fade(out * db(level), 0.01, 0.012), t0)
riser(29.25, tl.CHORUS, -20.0); boom(tl.CHORUS - 0.005, level=-8.0)
riser(7.12, tl.TITLE["t_full"], -25.0); boom(tl.TITLE["t0"], f0=64, f1=38, dur=0.7, level=-15.0)

mix = music + dialog + sfx
L = meter.integrated_loudness(mix[: int(35.5 * SR)]); mix *= db(-14.0 - L)
# look-ahead peak limiter to -1 dBFS
thr = db(-1.0); la = int(0.005 * SR); pk = np.abs(mix).max(1)
need = np.minimum(1.0, thr / np.maximum(pk, 1e-9))
from scipy.ndimage import minimum_filter1d, uniform_filter1d
g = minimum_filter1d(need, size=2 * la + 1); g = uniform_filter1d(g, size=la)
rel = np.empty_like(g); c = np.exp(-1 / (0.08 * SR)); acc = 1.0
for i in range(len(g)):
    acc = g[i] if g[i] < acc else 1 - (1 - acc) * c if True else acc
    acc = min(acc, 1.0) if g[i] >= acc else acc
    rel[i] = min(acc, g[i]) if g[i] < acc else acc
mix *= rel[:, None]; mix = np.clip(mix, -thr, thr)
mix[-int(0.25 * SR):] *= np.linspace(1, 0, int(0.25 * SR))[:, None]
sf.write(f"{R}/out/mix.wav", mix.astype(np.float32), SR)
np.save(f"{R}/out/stems_dbg.npy", np.stack([music.mean(1), dialog.mean(1), sfx.mean(1)]).astype(np.float32))
for name, x in (("music", music), ("dialog", dialog), ("sfx", sfx)):
    print(name, "peak dBFS", round(20 * np.log10(np.abs(x).max() + 1e-9), 1))
print("mix LUFS", round(meter.integrated_loudness(mix[: int(35.5 * SR)]), 2), "peak", round(20 * np.log10(np.abs(mix).max()), 2), "pre-norm L", round(L, 2), "min limiter gain dB", round(20 * np.log10(rel.min()), 2))
