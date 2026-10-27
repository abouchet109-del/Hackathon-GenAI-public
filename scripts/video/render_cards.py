"""Render the title cards of the submission video (1920x1080 PNG) with the Steward brand fonts."""
from playwright.sync_api import sync_playwright
import pathlib, os
ROOT=pathlib.Path(__file__).resolve().parents[2]
BR=(ROOT/'app/static/brand').as_uri()
os.makedirs(ROOT/'docs/submission/video/cards', exist_ok=True); os.chdir(ROOT/'docs/submission/video/cards')
HEAD=f'''<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:Archivo;src:url({BR}/fonts/Archivo-Variable.woff2);font-weight:100 900}}
@font-face{{font-family:"Chivo Mono";src:url({BR}/fonts/ChivoMono-Variable.woff2);font-weight:100 900}}
html,body{{margin:0;width:1920px;height:1080px;background:#0c121c;color:#f2f3f6;font-family:Archivo,sans-serif;overflow:hidden}}
.w{{position:absolute;inset:0;padding:140px 170px;display:flex;flex-direction:column;justify-content:center;gap:34px}}
.k{{font:500 28px "Chivo Mono",monospace;color:#999fa9;letter-spacing:.04em;text-transform:uppercase}}
h1{{font-weight:750;font-size:104px;line-height:1.02;margin:0;letter-spacing:-.02em}}
h2{{font-weight:650;font-size:68px;line-height:1.12;margin:0;letter-spacing:-.01em;max-width:1500px}}
p{{font-size:38px;line-height:1.4;margin:0;color:#c9ccd3;max-width:1450px}}
.m{{background:#f5e43b;color:#121926;padding:0 .18em;border-radius:4px}}
.s{{text-decoration:line-through;text-decoration-color:#f2a89e;text-decoration-thickness:6px;color:#999fa9}}
.row{{display:flex;gap:26px;flex-wrap:wrap}}
.chip{{font:600 34px Archivo,sans-serif;border:2px solid #2e3644;border-radius:12px;padding:18px 28px;background:#121926}}
.chip b{{display:block;font:500 22px "Chivo Mono",monospace;color:#999fa9;margin-top:8px;font-weight:400}}
.foot{{position:absolute;left:170px;bottom:80px;font:500 24px "Chivo Mono",monospace;color:#6b7280}}
</style></head><body>'''
cards={
"01-title":'<div class="w"><div class="k">Open Agent Hackathon 2026 · Track 3 · Team OSEF</div><h1>Steward</h1><h2>Keep the record <span class="m">straight.</span></h2><p>One company context for every AI your team already uses.</p></div>',
"02-problem":'<div class="w"><div class="k">The problem</div><h2>At Brikk, 12 people use 6 different AIs.</h2><p>Each AI knows a different, partial, outdated version of the company. The price is <span class="s">29 EUR</span> in one chat and 19 EUR in another. Nobody knows which one is true.</p></div>',
"03-solution":'<div class="w"><div class="k">The idea</div><h2>Steward plugs into each person\'s own AI over MCP.</h2><div class="row"><div class="chip">Watch<b>excerpts on watched topics, never the raw chat</b></div><div class="chip">Truth<b>store · supersede · clarify · escalate · redact · quarantine</b></div><div class="chip">Context<b>~1,500 tokens per role and task, every line cited</b></div></div><p>Sources are weighted by role × domain. A contradiction is first checked with its author, then escalated to whoever has authority.</p></div>',
"04-demo":'<div class="w"><div class="k">Demo</div><h2>The CEO console, driven live.</h2><p>Every proposal below goes through the full pipeline: guard, Zetaris governance, H-MEM recall, arbiter and judge.</p></div>',
"05-terminal":'<div class="w"><div class="k">Same pipeline, from the MCP side</div><h2>Eight steps, one trace per arbitration.</h2><p>Onboarding, two roles asking the same question, the watch layer, a clarification, a CEO policy, a replaced price, a blocked secret and a blocked injection.</p></div>',
"06-stack":'<div class="w"><div class="k">Built on</div><div class="row"><div class="chip">Zetaris<b>one SQL door over 3 sources + semantic layer</b></div><div class="chip">Meterless H-MEM<b>versioned company memory, 13/13 conformance</b></div><div class="chip">Meterless Nightshift<b>fast · deep · judge lanes</b></div><div class="chip">NVIDIA Nemotron<b>pinned on every lane</b></div><div class="chip">Cursor<b>dev environment and MCP client</b></div></div><p>Offline ablation on 34 labelled cases: without memory 56% correct and 3 unsafe writes; with H-MEM 100%, and the CEO is asked 3× less often.</p></div>',
"07-end":'<div class="w"><div class="k">github.com/rdalierdulys-arch/steward</div><h1>Steward</h1><h2>Keep the record <span class="m">straight.</span></h2><p>People keep their AI. The company keeps one truth.</p></div>',
}
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={"width":1920,"height":1080})
    for n,html in cards.items():
        f=pathlib.Path(f"{n}.html").resolve(); f.write_text(HEAD+html+'<div class="foot">Brikk is fictional. All data is synthetic.</div></body></html>')
        pg.goto(f.as_uri()); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(400)
        pg.screenshot(path=f"{n}.png")
    b.close()
print("ok")
