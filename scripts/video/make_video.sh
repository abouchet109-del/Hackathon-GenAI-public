#!/bin/bash
# Assemble the submission video (about 3.5 min, 1080p) from the title cards and the two recordings.
#   python scripts/video/render_cards.py
#   python scripts/video/record_console.py      (app running on a fresh STEWARD_SPACE=video)
#   python scripts/video/record_terminal.py --cmd "python run.py steward-demo" --out docs/submission/video/demo-terminal.mp4 --speed 1.6
#   bash scripts/video/make_video.sh
set -euo pipefail
cd "$(dirname "$0")/../../docs/submission/video"
mk(){ ffmpeg -loglevel error -y -loop 1 -t "$2" -i "cards/$1.png" -vf "fade=t=in:st=0:d=0.4,fade=t=out:st=$(echo "$2-0.4"|bc):d=0.4,format=yuv420p" -r 30 -c:v libx264 -crf 18 "seg_$1.mp4"; }
mk 01-title 4; mk 02-problem 7; mk 03-solution 9; mk 04-demo 4; mk 05-terminal 5; mk 06-stack 9; mk 07-end 5
ffmpeg -loglevel error -y -i console-walkthrough.mp4 -vf "setpts=PTS/1.12,fps=30,format=yuv420p" -c:v libx264 -crf 18 seg_console.mp4
TERM_CLIP=demo-terminal.mp4; [ -f "$TERM_CLIP" ] || TERM_CLIP=demo-terminal-offline.mp4
ffmpeg -loglevel error -y -i "$TERM_CLIP" -vf "scale=1920:1080,fps=30,format=yuv420p" -c:v libx264 -crf 18 seg_term.mp4
printf "file '%s'\n" seg_01-title.mp4 seg_02-problem.mp4 seg_03-solution.mp4 seg_04-demo.mp4 seg_console.mp4 \
  seg_05-terminal.mp4 seg_term.mp4 seg_06-stack.mp4 seg_07-end.mp4 > list.txt
ffmpeg -loglevel error -y -f concat -safe 0 -i list.txt -c copy -movflags +faststart steward-demo.mp4
rm -f seg_*.mp4 list.txt
echo "docs/submission/video/steward-demo.mp4 ($(ffprobe -v error -show_entries format=duration -of csv=p=0 steward-demo.mp4) s)"
