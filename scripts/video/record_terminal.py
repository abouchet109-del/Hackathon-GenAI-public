"""Record a REAL command run as a clean 1080p terminal video for the demo (no retakes needed).

The command is actually executed; its output (stderr + stdout, in order) is replayed line by line in a
terminal styled with the Steward brand, and recorded with Playwright. Nothing is typed by hand.

  python scripts/video/record_terminal.py --cmd "python run.py steward-demo" --out docs/submission/video/demo-terminal.mp4
Options: --title "...", --speed 1.0 (lines per ~0.45 s), --keep-html
Needs: playwright (python) with Chromium, ffmpeg.
"""
from __future__ import annotations

import argparse
import html
import json
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Chivo+Mono:wght@400;600&family=Archivo:wght@500;650&display=swap" rel="stylesheet">
<style>
html,body{margin:0;background:#0c121c;width:1920px;height:1080px;overflow:hidden}
.bar{height:56px;display:flex;align-items:center;gap:12px;padding:0 28px;background:#121926;border-bottom:1px solid #242b39;
 font:500 20px Archivo,system-ui,sans-serif;color:#b9bec6}
.dot{width:14px;height:14px;border-radius:50%;background:#2e3644}
.title{margin-left:16px}.title b{color:#f2f3f6;font-weight:650}
#t{padding:28px 40px;font:400 24px/1.55 'Chivo Mono',Menlo,monospace;color:#f2f3f6;white-space:pre-wrap;height:960px;overflow:hidden}
.cmd{color:#f5e43b}.dim{color:#999fa9}.ok{color:#7dd3a3}.human{color:#beb4f3}.blocked{color:#f2a89e}
.mark{background:#f5e43b;color:#121926;padding:0 4px;border-radius:2px}
</style></head><body>
<div class="bar"><span class="dot"></span><span class="dot"></span><span class="dot"></span><span class="title">§ <b>Steward</b> · __TITLE__</span></div>
<div id="t"></div>
<script>
const LINES = __LINES__; const SPEED = __SPEED__;
const t = document.getElementById('t');
function cls(l){ if(/->\\s*(STORE|SUPERSEDE)/.test(l)) return 'ok'; if(/->\\s*(CLARIFY|ESCALATE)|\\[medium\\]|\\[high\\]|meeting/.test(l)) return 'human';
  if(/->\\s*(REDACT|QUARANTINE)/.test(l)) return 'blocked'; if(/^\\s*(Stack|Brikk|Shared truth)/.test(l)) return 'dim'; return ''; }
async function run(){ const p=document.createElement('div'); p.className='cmd'; t.appendChild(p);
  for(const ch of '$ '+LINES.cmd){ p.textContent+=ch; await new Promise(r=>setTimeout(r,35)); }
  await new Promise(r=>setTimeout(r,700));
  for(const l of LINES.out){ const d=document.createElement('div'); d.className=cls(l); d.textContent=l||' '; t.appendChild(d);
    while(t.scrollHeight>t.clientHeight && t.children.length>1) t.removeChild(t.children[0]);
    await new Promise(r=>setTimeout(r, (/^\\d\\./.test(l)?900:450)/SPEED)); }
  document.title='done'; }
run();
</script></body></html>"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cmd", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="live run")
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--max-lines", type=int, default=80)
    ap.add_argument("--keep-html", action="store_true")
    args = ap.parse_args()

    proc = subprocess.run(args.cmd, shell=True, cwd=ROOT, capture_output=True, text=True)
    out = proc.stderr.splitlines()  # the demos narrate on stderr; JSON results go to stdout
    if not out:
        out = proc.stdout.splitlines()
    out = out[: args.max_lines]
    page = (PAGE.replace("__TITLE__", html.escape(args.title))
            .replace("__LINES__", json.dumps({"cmd": args.cmd, "out": out}, ensure_ascii=False))
            .replace("__SPEED__", str(args.speed)))
    work = Path(tempfile.mkdtemp())
    (work / "terminal.html").write_text(page, encoding="utf-8")

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080},
                                  record_video_dir=str(work), record_video_size={"width": 1920, "height": 1080})
        page_ = ctx.new_page()
        page_.goto((work / "terminal.html").as_uri())
        page_.wait_for_function("document.title === 'done'", timeout=10 * 60 * 1000)
        time.sleep(2.5)
        video = page_.video.path()
        ctx.close()
        browser.close()
    out_path = (ROOT / args.out) if not Path(args.out).is_absolute() else Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-r", "30", "-movflags", "+faststart", str(out_path)], check=True)
    if args.keep_html:
        shutil.copy(work / "terminal.html", out_path.with_suffix(".html"))
    print(f"{out_path} ({out_path.stat().st_size // 1024} KB) from: {shlex.quote(args.cmd)} exit={proc.returncode}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
