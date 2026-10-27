"""Record a guided walkthrough of the Steward console as a 1080p video (no hands needed).

Start the app first on a fresh space, then run:
  STEWARD_SPACE=video python run.py serve          # in another terminal
  python scripts/video/record_console.py --out docs/submission/video/console-walkthrough.mp4

The script drives the real console: an AI proposes, Steward rules, the author answers, the CEO rules,
then two people get two different contexts. A visible cursor and captions make it readable in a video.
Needs: playwright (python) with Chromium, ffmpeg.
"""
from __future__ import annotations

import argparse
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

OVERLAY = """
(() => {
  if (document.getElementById('__cur')) return;
  const c = document.createElement('div'); c.id = '__cur';
  c.style.cssText = 'position:fixed;z-index:99999;left:0;top:0;width:22px;height:22px;border-radius:50%;'
    + 'background:rgba(245,228,59,.85);border:2px solid #121926;pointer-events:none;transform:translate(-50%,-50%);'
    + 'transition:left .45s ease,top .45s ease,width .15s,height .15s';
  document.body.appendChild(c);
  const cap = document.createElement('div'); cap.id = '__cap';
  cap.style.cssText = 'position:fixed;z-index:99998;left:50%;top:10px;pointer-events:none;transform:translateX(-50%);max-width:900px;'
    + 'background:#121926;color:#f2f3f6;font:600 21px/1.35 Archivo,system-ui,sans-serif;padding:14px 26px;'
    + 'border-radius:10px;box-shadow:0 8px 30px rgba(0,0,0,.35);opacity:0;transition:opacity .3s';
  document.body.appendChild(cap);
  window.__caption = (t) => { cap.textContent = t; cap.style.opacity = t ? 1 : 0; };
  window.__move = (x, y) => { c.style.left = x + 'px'; c.style.top = y + 'px'; };
  window.__press = () => { c.style.width = '14px'; c.style.height = '14px';
    setTimeout(() => { c.style.width = '22px'; c.style.height = '22px'; }, 180); };
})();
"""


class Guide:
    def __init__(self, page, pace: float):
        self.p, self.pace = page, pace

    def wait(self, s: float):
        self.p.wait_for_timeout(int(s * 1000 * self.pace))

    def overlay(self):
        self.p.evaluate(OVERLAY)

    def caption(self, text: str, hold: float = 2.2):
        self.overlay()
        self.p.evaluate("t => window.__caption(t)", text)
        self.wait(hold)

    def point(self, selector: str):
        self.overlay()
        el = self.p.locator(selector).first
        el.scroll_into_view_if_needed()
        box = el.bounding_box()
        if box:
            self.p.evaluate("([x,y]) => window.__move(x,y)", [box["x"] + box["width"] / 2, box["y"] + box["height"] / 2])
        self.wait(0.6)
        return el

    def click(self, selector: str, after: float = 1.2):
        el = self.point(selector)
        self.p.evaluate("() => window.__press()")
        try:
            el.click(timeout=6000)
        except Exception:
            self.p.screenshot(path=str(ROOT / "logs" / "record_console_click.png"))
            print(f"click on {selector} was slow; forcing it", flush=True)
            el.click(force=True)
        self.wait(after)

    def type(self, selector: str, text: str):
        el = self.point(selector)
        el.click()
        el.fill("")
        el.type(text, delay=int(28 * self.pace))
        self.wait(0.5)

    def select(self, selector: str, label: str):
        self.point(selector)
        self.p.select_option(selector, value=label)
        self.wait(0.6)

    def tab(self, name: str, after: float = 1.6):
        self.click(f'a[data-tab="{name}"]', after)


def propose(g: Guide, member: str, ai: str, kind: str, text: str, topic: str = ""):
    g.tab("simulate", 0.8)
    g.select("#sim-member", member)
    g.select("#sim-ai", ai)
    g.select("#sim-kind", kind)
    g.select("#sim-topic", topic)
    g.type("#sim-content", text)
    g.click("#sim-go", 2.4)
    g.point("#sim-result")
    g.wait(2.0)


def scenario(g: Guide, base: str):
    p = g.p
    p.goto(f"{base}/console#truth")
    p.wait_for_selector("#records li")
    g.caption("Steward: one shared truth for every AI at Brikk, a 12-person startup.", 3.0)
    g.point("#records li:nth-child(5)")
    g.caption("Each record keeps who said it, from which AI, and which decision it replaced.", 3.0)

    g.caption("Julie works in ChatGPT. Her AI sends Steward a new price she told a customer.", 2.6)
    propose(g, "Julie Caron", "ChatGPT", "decision", "The price is now 19 EUR per user per month.", "pricing")
    g.caption("It contradicts the current record. Steward asks Julie first: error, or real change?", 3.2)

    g.tab("clarify")
    g.caption("Julie confirms: it is a real change, agreed with two pilots.", 2.4)
    g.type("#clarifications input[data-note]", "Agreed with two pilots as a launch offer.")
    g.click('#clarifications button[data-a="change"]', 2.0)

    g.caption("Inès (marketing, ChatGPT) books a trade show above her 10,000 EUR limit.", 2.6)
    propose(g, "Inès Roux", "ChatGPT", "decision", "Book a booth at Batimat Paris for 11,500 EUR.", "marketing_spend")
    g.caption("Above her authority: Steward escalates to the CEO instead of writing it.", 3.0)

    g.tab("queue", 2.0)
    g.caption("The CEO queue: Julie's price change and Inès's booth wait for a ruling.", 3.0)
    g.point('#pending section:has-text("Batimat")')
    g.click('#pending section:has-text("Batimat") [data-raise]', 0.8)
    g.type('#pending section:has-text("Batimat") input[data-draft]', "Marketing may commit up to 12,000 EUR per trade show without asking me.")
    g.caption("Claire approves once and raises a standing policy for next time.", 2.4)
    g.click('#pending section:has-text("Batimat") button[data-d="store"]', 2.4)
    g.point("#signals")
    g.caption("Weak signals: the CEO agent sees tension on pricing and suggests a meeting.", 3.4)

    g.caption("Tom (Gemini) books another show at 11,800 EUR. The policy now applies.", 2.6)
    propose(g, "Tom Girard", "Gemini", "decision", "Book a booth at Bois & Bati Lyon for 11,800 EUR.", "marketing_spend")
    g.caption("Stored directly, citing the CEO's policy. No new escalation.", 3.0)

    g.caption("Protection: a secret pasted into Cursor never enters the record.", 2.4)
    propose(g, "Léa Martin", "Cursor", "fact",
            "For tests, the staging database password is Brikk2026! and the API key is sk-live-EXAMPLE0000FAKE.", "tech_stack")
    g.wait(1.0)

    g.tab("context")
    g.caption("Same company, same question, two roles: what each AI actually receives.", 2.6)
    g.select("#ctx-member", "Claire Morel")
    g.type("#ctx-task", "What should I keep in mind for the launch?")
    g.click("#ctx-go", 2.4)
    g.point("#ctx-text")
    g.wait(2.6)
    g.select("#ctx-member", "Sami Haddad")
    g.click("#ctx-go", 2.4)
    g.point("#ctx-text")
    g.caption("The CEO gets money and policy; the CTO gets scope and stack. About 1,500 tokens each.", 3.4)
    g.tab("truth", 1.4)
    g.caption("Steward. Keep the record straight.", 3.0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--out", default="docs/submission/video/console-walkthrough.mp4")
    ap.add_argument("--pace", type=float, default=1.0, help=">1 slower, <1 faster")
    ap.add_argument("--dark", action="store_true")
    ap.add_argument("--zoom", type=float, default=1.4, help="UI scale in the 1080p frame (1 = tiny desktop UI)")
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright
    work = Path(tempfile.mkdtemp())
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        vw, vh = int(1920 / args.zoom) // 2 * 2, int(1080 / args.zoom) // 2 * 2
        ctx = browser.new_context(viewport={"width": vw, "height": vh}, device_scale_factor=1,
                                  color_scheme="dark" if args.dark else "light",
                                  record_video_dir=str(work), record_video_size={"width": vw, "height": vh})
        page = ctx.new_page()
        g = Guide(page, args.pace)
        try:
            scenario(g, args.base)
        finally:
            time.sleep(1.0)
            video = page.video.path()
            ctx.close()
            browser.close()
    out = Path(args.out) if Path(args.out).is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-vf", "scale=1920:1080:flags=lanczos",
                    "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-r", "30", "-movflags", "+faststart", str(out)], check=True)
    print(f"{out} ({out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
