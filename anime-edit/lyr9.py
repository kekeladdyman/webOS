import soundfile as sf, numpy as np, librosa, json, sys
from faster_whisper import WhisperModel
m = WhisperModel("large-v3", device="cpu", compute_type="int8", cpu_threads=3)
out = {}
for nm, path in (("vocals", "song2/sep/htdemucs/raw/vocals.wav"), ("mix", "song2/raw.wav")):
    y, sr = sf.read(path); y = librosa.resample(y.mean(1).astype(np.float32), orig_sr=sr, target_sr=16000)
    segs, _ = m.transcribe(y, language="en", beam_size=5, word_timestamps=True, vad_filter=False, condition_on_previous_text=False, temperature=0.0)
    ws = [(round(w.start, 2), round(w.end, 2), w.word.strip(), round(w.probability, 2)) for s in segs for w in s.words]; out[nm] = ws
    print(nm, " ".join(f"{w[2]}@{w[0]}({w[3]})" for w in ws), flush=True)
json.dump(out, open("song2/words_large.json", "w"))
