"""V8 soundtrack (feedback 6): every effect is made to sit IN the song.
SYNTHETIC is in C# minor; its bass walks A - G# - C# - D#/E. Hits are 808s tuned to the bass note under them, swells are the song's
own next beat reversed through a reverb, risers end exactly on the downbeat, the "What?" ad-libs get tempo-synced delay throws,
the pre-drop roll is cut from the song's drum stem. No library sparkles, chimes, bells or whooshes."""
import json, numpy as np, soundfile as sf, scipy.signal as sig, pyloudnorm as pyln, librosa
from scipy.ndimage import minimum_filter1d, uniform_filter1d
import tl8 as tl
SR = 48000; R = tl.ROOT; N = int(tl.END * SR)
rng = np.random.default_rng(8); meter = pyln.Meter(SR)
BPM = 123.05; BEAT = 60.0 / BPM; S16 = BEAT / 4
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
def conv(x, ir): return np.stack([sig.fftconvolve(x[:, c], ir[:, c]) for c in range(2)], 1)
def st(x): return np.stack([x, x], 1) if x.ndim == 1 else x
def loud(y, target):
    yy = st(y); pad = np.zeros((int(0.5 * SR), 2))
    L = meter.integrated_loudness(np.concatenate([pad, yy, yy, yy, pad]) if len(yy) < 1.5 * SR else yy)
    return y * db(target - L) if np.isfinite(L) else y

# ------------------------------------------------------------ song (SYNTHETIC, uninterrupted, ends 40.55)
song, sr = sf.read(f"{R}/song2/raw.wav", dtype="float32"); assert sr == SR
STEM = {k: sf.read(f"{R}/song2/sep/htdemucs/raw/{k}.wav", dtype="float32")[0].astype(np.float64) for k in ("vocals", "drums", "bass", "other")}
_n = min(len(song), *(len(v) for v in STEM.values())); vd = np.ones(_n)
for a_, b_ in ((0.20, 1.80), (2.45, 6.10)): vd[int(a_ * SR):int(b_ * SR)] = db(-16.0)
_k = int(0.08 * SR); vd = np.convolve(vd, np.ones(_k) / _k, mode="same")
_rebuilt = STEM["vocals"][:_n] * vd[:, None] + STEM["drums"][:_n] + STEM["bass"][:_n] + STEM["other"][:_n]
_sw = np.zeros(_n); _sw[: int(7.0 * SR)] = 1.0; _sw[int(7.0 * SR):int(7.2 * SR)] = np.linspace(1, 0, int(0.2 * SR))
song = song.copy().astype(np.float64); song[:_n] = song[:_n] * (1 - _sw[:, None]) + _rebuilt * _sw[:, None]
song = fade(song[: int(tl.SONG_END * SR)], 0.005, 0.05)
SG = db(-15.0 - meter.integrated_loudness(song[int(8 * SR): int(31 * SR)])); song *= SG
for k in STEM: STEM[k] = STEM[k] * SG
music = np.zeros((N, 2)); place(music, song, 0.0)
duck = np.ones(N)
for a_, b_, g_ in ((0.20, 1.85, -6.0), (2.45, 4.00, -9.0), (4.00, 6.10, -7.0)): duck[int(a_ * SR):int(b_ * SR)] = db(g_)
k = int(0.20 * SR); duck = np.convolve(duck, np.ones(k) / k, mode="same"); music *= duck[:, None]
tail_src = np.zeros((N, 2)); s0, s1 = int(38.6 * SR), int(tl.SONG_END * SR)
w = np.ones(s1 - s0); w[: int(0.8 * SR)] = np.linspace(0, 1, int(0.8 * SR)); tail_src[s0:s1] = music[s0:s1] * w[:, None]
music += conv(tail_src, reverb_ir(6.0, 1.9, 2600))[:N] * db(-10.0)

# ------------------------------------------------------------ dialogue (unchanged from v20)
def dstem(name, a, b):
    y, sr = sf.read(f"{R}/dlg/sep/htdemucs/{name}/vocals.wav", dtype="float32")
    return librosa.resample(y[int(a * sr): int(b * sr)].mean(1).astype(np.float64), orig_sr=sr, target_sr=SR)
def line(name, a, b, gate_db=-46):
    y = butter(dstem(name, a, b), 85, "high", 2); w = int(0.02 * SR)
    e = np.sqrt(np.convolve(y ** 2, np.ones(w) / w, mode="same") + 1e-12)
    g = np.clip((20 * np.log10(e + 1e-9) - gate_db) / 10.0, 0.0, 1.0); g = np.convolve(g, np.ones(w) / w, mode="same")
    return fade(y * g, 0.03, 0.10)
PRE = 0.12
segs = [("raw_body", 0.05 - 0.02, 1.52, 0.30), ("raw_body", 9.535, 10.98, 2.62 + PRE), ("raw_body", 11.58 - PRE, 13.52, 4.06),
        ("raw_inside2", 10.40 - PRE, 14.70, tl.TAG_T)]
dry = np.zeros((N, 2)); grp = {}
for nm, a, b, t in segs: grp.setdefault(nm, []).append((a, b, t))
for nm, items in grp.items():
    parts = [line(nm, a, b) for a, b, _ in items]; allp = loud(np.concatenate(parts), -15.0); k = 0
    for p, (_, _, t) in zip(parts, items):
        q = allp[k:k + len(p)]; k += len(p); place(dry, np.tanh(q * 1.15) / 1.15, t - PRE)
dialog = dry + conv(dry, reverb_ir(2.2, 0.55, 6000))[:N] * db(-15.0)

# ------------------------------------------------------------ musical effects
sfx = np.zeros((N, 2)); LOG = []
BN = json.load(open(f"{R}/song2/bassnotes.json"))
NOTE_HZ = {"A": 55.0, "A#": 58.27, "B": 61.74, "C": 65.41, "C#": 69.30, "D": 73.42, "D#": 77.78, "E": 41.20, "F": 43.65, "F#": 46.25, "G": 49.0, "G#": 51.91}
def note_at(t, override=None):
    if override: return NOTE_HZ[override]
    cur = BN[0][1]
    for bt, nm, _ in BN:
        if bt <= t + 0.06: cur = nm
    return NOTE_HZ[cur]
def e808(t, f=None, dur=0.9, level=-14.0, drive=2.2, glide=7.0, tau=None, lp=1400, note=None):
    """808: tuned sine with a fast pitch-drop attack, saturated so its harmonics carry on phone speakers."""
    f = f or note_at(t, note); n = int(dur * SR); tt = np.arange(n) / SR
    fr = f * 2 ** (glide / 12 * np.exp(-tt / 0.035)); ph = 2 * np.pi * np.cumsum(fr) / SR
    env = np.exp(-tt / (tau or dur * 0.45)); env[: int(0.003 * SR)] *= np.linspace(0, 1, int(0.003 * SR))
    x = np.tanh(np.sin(ph) * drive * env) / np.tanh(drive); x = butter(x, lp, "low", 2)
    place(sfx, fade(x * db(level), 0.001, 0.05), t); LOG.append((round(t, 2), "808", round(f, 1)))
def kick(t, level=-18.0, f1=None):
    n = int(0.32 * SR); tt = np.arange(n) / SR; f1 = f1 or note_at(t) * (1 if note_at(t) < 60 else 0.5) * 1.0
    fr = f1 + (170 - f1) * np.exp(-tt / 0.022); x = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-tt / 0.10)
    cl = butter(rng.normal(0, 1, n), 2500, "high", 2) * np.exp(-tt / 0.004) * 0.35
    place(sfx, fade((x + cl) * db(level), 0.0005, 0.03), t); LOG.append((round(t, 2), "kick", level))
def crack(t, level=-24.0, tone=1800, dec=0.045, wet=-10.0):
    """a snare-like transient (filtered noise) with a short room - on the beat it reads as part of the drums."""
    n = int(0.25 * SR); tt = np.arange(n) / SR; x = butter(rng.normal(0, 1, n), [tone * 0.5, tone * 3.0], "band", 2) * np.exp(-tt / dec)
    y = st(x) * db(level); y = y + conv(y, reverb_ir(1.2, 0.35, 7000))[: len(y) + int(1.2 * SR)][:len(y)] * db(wet)
    place(sfx, fade(y, 0.0005, 0.05), t); LOG.append((round(t, 2), "crack", level))
def thwack(t, level=-27.0):
    """paper / panel slam: a dull low-passed noise slap - percussive, no pitch."""
    n = int(0.12 * SR); tt = np.arange(n) / SR; x = butter(rng.normal(0, 1, n), 1600, "low", 2) * np.exp(-tt / 0.018)
    place(sfx, fade(x * db(level), 0.0005, 0.02), t)
def rev_swell(t_end, dur=0.5, level=-22.0, src="mix", look=0.7, hp=180, decay=1.1):
    """the song's own next moment, reverbed and reversed so it sucks into the hit at t_end (always in key, always in time)."""
    a = int(t_end * SR); srcarr = music if src == "mix" else STEM[src]; b = min(len(srcarr), a + int(look * SR))
    seg = srcarr[a:b].copy() if b - a > int(0.05 * SR) else np.zeros((int(look * SR), 2))
    seg = st(seg) if seg.ndim == 1 else seg
    if np.abs(seg).max() < 1e-6: print("rev_swell: silent source at", t_end); return
    wet = conv(fade(seg, 0.002, 0.05), reverb_ir(2.6, decay, 6500)); rv = wet[::-1]
    rv = rv[-int(dur * SR):]; rv = butter(rv, hp, "high", 2); rv = rv * np.linspace(0, 1, len(rv))[:, None] ** 1.8
    rv = loud(rv, level); place(sfx, fade(rv, 0.05, 0.003), t_end - len(rv) / SR); LOG.append((round(t_end, 2), "rev_swell", level))
def swept(n, fc, bw=0.55):
    """white noise through a band-pass whose centre follows fc[n] (Hz), done in the STFT domain (click-free)."""
    x = rng.normal(0, 1, n + 4096); f, tt_, Z = sig.stft(x, SR, nperseg=2048, noverlap=1536)
    idx = np.clip((tt_ * SR).astype(int), 0, n - 1); c = fc[idx]
    lf = np.log2(np.maximum(f, 1.0))[:, None]; m = np.exp(-0.5 * ((lf - np.log2(c)[None, :]) / bw) ** 2)
    _, y = sig.istft(Z * m, SR, nperseg=2048, noverlap=1536); return y[:n]
def riser(t0, t1, level=-24.0, f0=250, f1=7000, trem=True, tone=True):
    n = int((t1 - t0) * SR); tt = np.arange(n) / SR; u = tt / (t1 - t0)
    out = swept(n, f0 * (f1 / f0) ** (u ** 1.6))
    if tone:                                                   # C# minor triad rising an octave into the drop
        for f in (138.6, 164.8, 207.7):
            ph = 2 * np.pi * np.cumsum(f * 2 ** (u ** 2)) / SR; out += 0.05 * np.std(out) / 0.3 * (2 * ((ph / (2 * np.pi)) % 1) - 1) * u
    env = u ** 2.2
    if trem: env = env * (0.55 + 0.45 * np.tanh(6 * np.sin(2 * np.pi * tt / S16 + 0.3)) * np.clip(u * 1.3, 0, 1))
    y = st(out * env); y[:, 1] = np.roll(y[:, 1], 41); y = loud(y, level)
    y[-int(0.004 * SR):] *= np.linspace(1, 0, int(0.004 * SR))[:, None]; place(sfx, y, t0); LOG.append((round(t1, 2), "riser", level))
def downlifter(t, dur=1.6, level=-27.0, f0=5000, f1=180):
    n = int(dur * SR); tt = np.arange(n) / SR; u = tt / dur; out = swept(n, f0 * (f1 / f0) ** (u ** 0.7))
    y = st(out * np.exp(-u * 2.6)); y = loud(y, level); place(sfx, fade(y, 0.002, 0.2), t)
def sub_drop(t, f0=None, dur=1.3, level=-15.0):
    f0 = f0 or note_at(t); n = int(dur * SR); tt = np.arange(n) / SR; fr = f0 * 2 ** (-np.clip(tt / dur, 0, 1) ** 1.3)
    x = np.tanh(np.sin(2 * np.pi * np.cumsum(fr) / SR) * 1.6) * np.exp(-tt / (dur * 0.5)); place(sfx, fade(x * db(level), 0.004, 0.2), t)
def throw(t0, t1, rel=-5.0, d=BEAT * 0.75, fb=0.45, reps=4):
    """delay throw on a vocal ad-lib: dotted-8th echoes, ping-pong, filtered."""
    a, b = int(t0 * SR), int(t1 * SR); v = STEM["vocals"][a:b].copy(); v = butter(fade(v, 0.005, 0.03), [450, 5200], "band", 2)
    out = np.zeros((len(v) + int(d * reps * SR) + 10, 2))
    for r in range(1, reps + 1):
        i = int(r * d * SR); g = fb ** (r - 1); side = np.array([1.0, 0.35]) if r % 2 else np.array([0.35, 1.0])
        out[i:i + len(v)] += v * g * side[None, :]
    out = butter(out, 3600, "low", 2); place(sfx, out * db(rel), t0); LOG.append((round(t0, 2), "throw", rel))
def roll(t0, t1, src_t, rel=-6.0):
    """beat-repeat roll from the drum stem: 1/8 -> 1/16 -> 1/32 slices of the hit at src_t, accelerating into t1."""
    n = int((t1 - t0) * SR); out = np.zeros((n, 2)); u0 = 0.0; t = 0.0
    while t < t1 - t0 - 0.005:
        u = t / (t1 - t0); L = S16 * 2 if u < 0.35 else S16 if u < 0.7 else S16 / 2
        a = int(src_t * SR); sl = fade(STEM["drums"][a:a + int(L * SR)].copy(), 0.001, 0.008) * (0.5 + 0.5 * u)
        i = int(t * SR); j = min(n, i + len(sl)); out[i:j] += sl[:j - i]; t += L
    out = butter(out, 120, "high", 2); place(sfx, out * db(rel), t0); LOG.append((round(t0, 2), "roll", rel))
def drone(t0, t1, level=-30.0, root=69.30):
    n = int((t1 - t0) * SR); tt = np.arange(n) / SR; u = tt / (t1 - t0)
    x = np.sin(2 * np.pi * root * tt) + 0.5 * np.sin(2 * np.pi * root * 1.5 * tt + 0.3) + 0.25 * np.sin(2 * np.pi * root * 2.0 * tt) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.25 * tt))
    env = np.clip(u / 0.25, 0, 1) * np.clip((1 - u) / 0.2, 0, 1); y = st(np.tanh(x * env * 0.8)); y[:, 1] = np.roll(y[:, 1], 211); place(sfx, loud(y, level), t0)
def rumble(t0, t1, level=-28.0, root=None):
    """the ゴゴゴ menace: a tuned low saw, slow filter wobble."""
    root = root or note_at(t0) / 2 * 2; n = int((t1 - t0) * SR); tt = np.arange(n) / SR; u = tt / (t1 - t0)
    saw = sum((1 / h) * np.sin(2 * np.pi * root * h * tt + h) for h in range(1, 14))
    y = butter(saw, 400, "low", 2) * (0.7 + 0.3 * np.sin(2 * np.pi * (1 / BEAT) * 2 * tt)) * np.clip(u / 0.15, 0, 1) * np.clip((1 - u) / 0.1, 0, 1)
    place(sfx, loud(st(y), level), t0)
def vstutter(t, src_t, L=S16 / 2, reps=4, rel=-4.0):
    a = int(src_t * SR); sl = fade(STEM["vocals"][a:a + int(L * SR)].copy(), 0.001, 0.004); out = np.concatenate([sl * (0.6 + 0.4 * i / reps) for i in range(reps)])
    place(sfx, butter(out, 300, "high", 2) * db(rel), t)
def hiss(t0, t1, level=-38.0):
    n = int((t1 - t0) * SR); y = butter(rng.normal(0, 1, (n, 2)), [500, 7000], "band", 2); place(sfx, fade(loud(y, level), 0.05, 0.08), t0)

C = tl.CHORUS
# -- intro: the manga page (dialogue on top - effects stay low and below the voice)
hiss(0.0, 0.81, -40.0)
for t_ in (0.81, 2.74, 4.67): e808(t_, dur=1.2, level=-21.0, drive=1.6, lp=300); thwack(t_, -29.0)          # each panel lands on the song's bass note
rev_swell(5.02, 0.55, -31.0, hp=400)                                                                            # into "...Shinoyama" (soft, under the voice)
rev_swell(6.11, 0.45, -24.0)                                                                                    # into the logo
# -- the official logo: DEAD / MOUNT / DEATH / full - a kick + 808 on each beat, walking the bass
for t_ in tl.LOGO_T[:4]: kick(t_, -19.0); e808(t_, dur=0.42, level=-19.0)
rev_swell(8.03, 0.42, -22.0)
# -- verse
e808(8.03, dur=0.9, level=-16.0); crack(8.03, -27.0); rumble(8.03, 8.74, -30.0)                                 # out of the eye socket, ゴゴゴ
e808(8.74, dur=0.5, level=-17.0); thwack(8.74, -25.0)                                                           # FACE
e808(9.46, dur=0.5, level=-17.0); thwack(9.46, -25.0); kick(9.94, -21.0)                                       # face to face
rev_swell(10.43, 0.30, -25.0); e808(10.43, dur=0.6, level=-16.0); crack(10.43, -27.0)                          # the knight's panel slams
kick(10.89, -23.0)
rev_swell(11.68, 0.30, -24.0); e808(11.68, dur=0.7, level=-15.0); crack(11.68, -25.0)                          # UNMASKED
rev_swell(12.35, 0.35, -23.0); e808(12.35, dur=0.9, level=-15.0); kick(12.82, -21.0)                           # ARMAGEDDON / strips re-slide
rev_swell(13.28, 0.40, -29.0, src="other", hp=600)                                                              # tears (soft)
rumble(14.26, 15.21, -28.0); e808(14.26, dur=0.8, level=-16.0); thwack(14.72, -26.0); thwack(14.96, -26.0)       # the army spread, ゴゴゴ
e808(15.21, dur=0.5, level=-15.0); crack(15.21, -25.0)                                                          # DEMONS
riser(15.21, C, -24.0); roll(15.72, C, 15.72, -6.0); rev_swell(C, 0.40, -21.0)                                # the build: riser + drum roll + suck-in
# -- the drop
e808(C, dur=1.6, level=-14.0, drive=2.6); crack(C, -21.0, tone=1500, dec=0.07); sub_drop(C + 0.02, dur=1.4, level=-17.0); downlifter(C + 0.05, 1.7, -28.0)
for t_ in (16.85, 17.57, 18.30): e808(t_, dur=0.55, level=-16.0); thwack(t_, -24.0)                           # panels slam with the 3-3-2 bass
rev_swell(19.01, 0.30, -23.0); e808(19.01, dur=0.8, level=-14.5); crack(19.01, -23.0, tone=2200)               # the page tears - the dragon
for wt in tl.WHAT: throw(wt, wt + 0.30, -5.0)                                                                  # "What?" delay throws
rev_swell(19.96, 0.30, -24.0); e808(19.96, dur=1.0, level=-15.0)                                                # light pillar (bass moves to C#)
rev_swell(20.40, 0.40, -24.0, src="other"); e808(20.40, dur=0.6, level=-18.0)                                   # the circle
e808(21.10, dur=0.5, level=-18.0); rev_swell(22.27, 0.32, -25.0); e808(22.27, dur=0.6, level=-17.0)            # circle -> eye, eye -> ghosts
rev_swell(22.86, 0.30, -24.0); e808(22.86, dur=0.8, level=-15.5); crack(22.86, -26.0)                          # Polka cut out of the crowd
e808(23.81, dur=0.6, level=-14.5); crack(23.81, -24.0)                                                          # Lemmings
for i_ in range(1, 6): thwack(23.81 + i_ * BEAT / 2, -30.0 + (i_ % 2) * 2)                                      # his stutter, on the 8ths
kick(24.53, -20.0); thwack(24.53, -24.0)
rev_swell(24.79, 0.25, -22.0); e808(24.79, dur=0.7, level=-14.0); crack(24.79, -22.0, tone=2600, dec=0.06)     # shatter
e808(25.25, dur=0.5, level=-15.5); thwack(25.25, -24.0); kick(25.61, -21.0)                                    # VS
e808(25.97, dur=0.6, level=-15.0); crack(25.97, -25.0)                                                          # Polka shouts
rev_swell(26.70, 0.28, -22.0); e808(26.70, dur=0.8, level=-14.0); crack(26.70, -22.0, tone=2400)               # sliced
rev_swell(27.65, 0.30, -23.0); e808(27.65, dur=0.6, level=-15.0); riser(27.65, 28.62, -29.0, f0=600, f1=5000, trem=True, tone=False)   # the spell
rev_swell(28.62, 0.25, -21.0); e808(28.62, dur=0.6, level=-13.5); crack(28.62, -22.0, tone=1300, dec=0.08)     # NECROMANCER
e808(28.92, dur=0.5, level=-16.0); thwack(28.92, -24.0)
e808(29.81, dur=0.6, level=-16.0); rev_swell(29.81, 0.25, -25.0)
rev_swell(30.55, 0.40, -20.0); e808(30.55, dur=1.8, level=-14.0, drive=2.6); crack(30.55, -21.0, tone=1500, dec=0.08); sub_drop(30.57, dur=1.5, level=-17.0)
downlifter(31.30, 1.8, -29.0)                                                                                   # into the outro
# -- outro
rev_swell(33.04, 0.45, -28.0, src="vocals", hp=300)                                                             # "mirror"
vstutter(34.46, 34.46, reps=4, rel=-3.0)                                                                     # "re-re-re-recognize" glitch, from his own vocal
rev_swell(36.52, 0.55, -27.0, src="vocals", hp=300)                                                             # "disappeared" sucks in
rev_swell(37.88, 0.30, -25.0); e808(37.88, dur=0.9, level=-17.0); thwack(37.88, -27.0)                         # MASK
rev_swell(40.06, 0.50, -28.0, src="mix", hp=300)                                                             # "nothing"
# -- tag: Lisa's line over a low C# drone; at "inside" the floor drops out
drone(40.55, 45.10, -33.0)
sub_drop(44.70, f0=69.30, dur=1.4, level=-18.0)
# -- end card
e808(tl.CARD_T, f=69.30, dur=1.4, level=-15.0, drive=2.0); crack(tl.CARD_T, -24.0, tone=1400, dec=0.07, wet=-6.0)

# ------------------------------------------------------------ bus: the 808s pump the song's low end (sidechain) so they never smear it
env808 = np.zeros(N)
for t_, kind, _ in LOG:
    if kind == "808":
        i = int(t_ * SR); L = int(0.22 * SR); j = min(N, i + L)
        if i < N: env808[i:j] = np.maximum(env808[i:j], np.linspace(1, 0, L)[: j - i] ** 1.5)
sc = 1 - (1 - db(-5.0)) * env808; lo = butter(music, 140, "low", 2); music = music - lo + lo * sc[:, None]
sfx = butter(sfx, 28, "high", 2)
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
sf.write(f"{R}/out/mix8.wav", mix.astype(np.float32), SR)
np.save(f"{R}/out/stems8_dbg.npy", np.stack([music.mean(1), dialog.mean(1), sfx.mean(1)]).astype(np.float32))
for name, x in (("music", music), ("dialog", dialog), ("sfx", sfx)): print(name, "peak dBFS", round(20 * np.log10(np.abs(x).max() + 1e-9), 1))
print("mix LUFS", round(meter.integrated_loudness(mix[: int(40.5 * SR)]), 2), "| pre-norm", round(L, 2), "| limiter max GR dB", round(20 * np.log10(rel.min()), 2), "|", len(LOG), "events")
