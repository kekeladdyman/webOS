"""Extract each timeline shot's source span to an all-intra RGB cache clip (1920x1080)."""
import subprocess, os, sys, json, hashlib
from concurrent.futures import ThreadPoolExecutor
import tl
os.makedirs(f"{tl.ROOT}/cache", exist_ok=True)

def src_dur(s):
    d = s["t1"] - s["t0"]
    sp = s["speed"]
    if isinstance(sp, (int, float)): return d * sp + 0.3
    return d * max(v for _, v in sp) + 0.3

def key(s):
    return hashlib.md5(f'{s["ep"]}_{s["ss"]:.3f}_{src_dur(s):.3f}'.encode()).hexdigest()[:10]

def run(s):
    out = f'{tl.ROOT}/cache/{key(s)}.mp4'
    if os.path.exists(out) and os.path.getsize(out) > 1000: return out
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f'{s["ss"]:.3f}', "-i", f'{tl.ROOT}/eps/ep{s["ep"]:02d}.mkv',
           "-t", f"{src_dur(s):.3f}", "-map", "0:v:0", "-an", "-sn",
           "-vf", "scale=1920:1080:flags=lanczos:in_color_matrix=bt709:in_range=tv:out_range=pc,format=gbrp",
           "-c:v", "libx264rgb", "-preset", "veryfast", "-crf", "8", "-g", "1", "-threads", "2", out + ".tmp.mp4"]
    subprocess.run(cmd, check=True); os.replace(out + ".tmp.mp4", out); return out

if __name__ == "__main__":
    with ThreadPoolExecutor(3) as ex: outs = list(ex.map(run, tl.SHOTS))
    tot = sum(os.path.getsize(o) for o in set(outs))
    print(len(outs), "clips,", round(tot / 1e6), "MB")
