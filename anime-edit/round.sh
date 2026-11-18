#!/bin/bash
# usage: round.sh NN   -> snapshot sources, mix audio, render 1080p60, export rounds/DMDP_experiment_vNN.mp4, run checks + review sheet
set -e
S=/tmp/claude-0/-home-user-webOS/d7747165-cfac-5f94-b285-20cb117742a0/scratchpad; cd $S; . venv/bin/activate
N=$1; V=$(printf "%02d" $N); mkdir -p rounds/src_v$V
cp tl4.py r2core.py render2.py render4.py render5.py render6.py audio6.py prep2.py rounds/src_v$V/
TLMOD=tl4 python prep2.py 2>&1 | grep -v "^$" | tail -1
python audio6.py | tail -1
t0=$(date +%s); python render6.py final 2>&1 | tail -1; echo "render $(( $(date +%s)-t0 ))s"
ffmpeg -v error -y -i out/final6_video.mp4 -i out/mix6.wav -map 0:v -map 1:a -c:v libx264 -preset slow -crf 20 -maxrate 14M -bufsize 28M -pix_fmt yuv420p \
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 -c:a aac -b:a 256k -movflags +faststart -shortest rounds/DMDP_experiment_v$V.mp4
rm -f out/final6_part*.mp4
ffprobe -v error -show_entries format=duration,size -of csv=p=0 rounds/DMDP_experiment_v$V.mp4
ffmpeg -hide_banner -nostats -i rounds/DMDP_experiment_v$V.mp4 -af ebur128=peak=true -f null - 2>&1 | tail -12 | grep -E "I:|Peak:" | tr -s ' ' | tr '\n' ' '; echo
python - <<PY
import cv2
cap=cv2.VideoCapture("rounds/DMDP_experiment_v$V.mp4"); fps=cap.get(cv2.CAP_PROP_FPS); b=[]; i=0
while True:
    ok,f=cap.read()
    if not ok: break
    t=i/fps
    if f[::8,::8].mean()<3 and 0.35<t<38.9: b.append(round(t,2))
    i+=1
print("frames",i,"black frames:",b[:20])
PY
python review.py rounds/DMDP_experiment_v$V.mp4 r$V 0.3 39.3 0.5 10 192 >/dev/null; mv out/rev_r$V.jpg rounds/rev_v$V.jpg; echo "sheet rounds/rev_v$V.jpg"
