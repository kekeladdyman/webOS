#!/bin/bash
# usage: round8.sh NN -> snapshot sources, mattes, mix, render 1080p60, export rounds/DMDP_experiment_vNN.mp4 + checks + review sheet
set -e
S=/tmp/claude-0/-home-user-webOS/d7747165-cfac-5f94-b285-20cb117742a0/scratchpad; cd $S; . venv/bin/activate
N=$1; V=$(printf "%02d" $N); mkdir -p rounds/src_v$V
cp tl8.py tl7.py r2core.py render2.py render4.py render5.py render6.py render7.py render8.py fxcomp.py fxtype.py audio8.py prep2.py prep8.py rounds/src_v$V/
TLMOD=tl8 python prep2.py 2>&1 | grep -v "^$" | tail -1
python audio8.py | tail -1
t0=$(date +%s); python render8.py final 2>&1 | tail -1; echo "render $(( $(date +%s)-t0 ))s"
ffmpeg -v error -y -i out/final8_video.mp4 -i out/mix8.wav -map 0:v -map 1:a -c:v libx264 -preset slow -crf 20 -maxrate 14M -bufsize 28M -pix_fmt yuv420p \
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 -c:a aac -b:a 256k -movflags +faststart -shortest rounds/DMDP_experiment_v$V.mp4
ffprobe -v error -show_entries format=duration,size -of csv=p=0 rounds/DMDP_experiment_v$V.mp4
ffmpeg -hide_banner -nostats -i rounds/DMDP_experiment_v$V.mp4 -af ebur128=peak=true -f null - 2>&1 | tail -12 | grep -E "I:|Peak:" | tr -s ' ' | tr '\n' ' '; echo
python review.py rounds/DMDP_experiment_v$V.mp4 r$V 0.3 47.3 0.6 10 192 >/dev/null; mv out/rev_r$V.jpg rounds/rev_v$V.jpg; echo "sheet rounds/rev_v$V.jpg"
