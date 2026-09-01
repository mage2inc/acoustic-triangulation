#!/usr/bin/env python3
"""Build a self-contained download page for node_report.pdf (PDF embedded as
base64 so the link downloads with no external host). Output: out/report_download.html"""
import base64, os
HERE=os.path.dirname(__file__); OUT=os.path.join(HERE,'out')
pdf=os.path.join(OUT,'node_report.pdf')
b64=base64.b64encode(open(pdf,'rb').read()).decode()
kb=os.path.getsize(pdf)//1024

HEAD = '''<title>Acoustic Node Carrier — PCB Inspection Packet</title>
<style>
  :root{
    --bg:#eef1f4; --surface:#ffffff; --ink:#1a2230; --muted:#5a6676;
    --line:#d7dde5; --accent:#b06a2c; --accent-soft:#f0e2d3; --copper:#c07a38;
    --good:#2f7d55;
  }
  @media (prefers-color-scheme:dark){
    :root{ --bg:#10151c; --surface:#182029; --ink:#e7ecf2; --muted:#9aa7b6;
      --line:#2a3644; --accent:#d68a4a; --accent-soft:#2a2018; --copper:#d68a4a; --good:#5cba86; }
  }
  :root[data-theme="light"]{ --bg:#eef1f4; --surface:#ffffff; --ink:#1a2230; --muted:#5a6676;
    --line:#d7dde5; --accent:#b06a2c; --accent-soft:#f0e2d3; --copper:#c07a38; --good:#2f7d55; }
  :root[data-theme="dark"]{ --bg:#10151c; --surface:#182029; --ink:#e7ecf2; --muted:#9aa7b6;
    --line:#2a3644; --accent:#d68a4a; --accent-soft:#2a2018; --copper:#d68a4a; --good:#5cba86; }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);
    font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;line-height:1.5;
    -webkit-font-smoothing:antialiased;padding:clamp(16px,4vw,48px)}
  .wrap{max-width:820px;margin:0 auto;display:flex;flex-direction:column;gap:22px}
  .card{background:var(--surface);border:1px solid var(--line);border-radius:14px;
    padding:clamp(20px,3vw,32px)}
  .eyebrow{font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace;font-size:12px;
    letter-spacing:.14em;text-transform:uppercase;color:var(--accent);margin:0 0 10px}
  h1{margin:0;font-size:clamp(24px,4vw,34px);line-height:1.1;letter-spacing:-.02em;text-wrap:balance}
  .sub{margin:8px 0 0;color:var(--muted);max-width:60ch}
  .stats{display:flex;flex-wrap:wrap;gap:10px;margin-top:22px}
  .chip{font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace;font-size:12.5px;
    border:1px solid var(--line);border-radius:999px;padding:6px 13px;color:var(--ink);
    background:transparent;white-space:nowrap}
  .chip b{color:var(--accent);font-weight:600}
  .chip.ok b{color:var(--good)}
  .dl{display:flex;flex-wrap:wrap;align-items:center;gap:16px;margin-top:26px}
  a.btn{display:inline-flex;align-items:center;gap:10px;background:var(--copper);color:#fff;
    text-decoration:none;font-weight:600;font-size:15px;padding:13px 22px;border-radius:10px;
    border:1px solid rgba(0,0,0,.12);transition:transform .12s ease,filter .12s ease}
  a.btn:hover{filter:brightness(1.06)}
  a.btn:active{transform:translateY(1px)}
  a.btn:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
  .btn svg{width:18px;height:18px;flex:none}
  .meta{font-family:ui-monospace,monospace;font-size:12.5px;color:var(--muted)}
  .note{display:flex;gap:12px;align-items:flex-start;background:var(--accent-soft);
    border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin-top:8px}
  .note .k{font-family:ui-monospace,monospace;font-size:11px;letter-spacing:.1em;
    text-transform:uppercase;color:var(--accent);font-weight:700;padding-top:1px}
  .note p{margin:0;font-size:14px}
  .preview{padding:0;overflow:hidden}
  .preview .bar{display:flex;justify-content:space-between;align-items:center;
    padding:12px 16px;border-bottom:1px solid var(--line);font-family:ui-monospace,monospace;
    font-size:12px;color:var(--muted)}
  iframe{width:100%;height:min(78vh,900px);border:0;display:block;background:#fff}
  footer{color:var(--muted);font-size:12.5px;font-family:ui-monospace,monospace;text-align:center;
    padding:4px 0 8px}
</style>'''

BODY = f'''<div class="wrap">
  <div class="card">
    <p class="eyebrow">Acoustic triangulation · node carrier</p>
    <h1>PCB Inspection Packet</h1>
    <p class="sub">Everything for a design review before any copper is cut — placement, routed
    copper, and a 1:1 template you print at 100&#37; to check that every part physically fits.</p>
    <div class="stats">
      <span class="chip"><b>5656&#215;50&nbsp;mm#215;5356&#215;50&nbsp;mmnbsp;mm</b> board</span>
      <span class="chip"><b>2-layer</b> milled</span>
      <span class="chip ok"><b>0</b> copper crossings</span>
      <span class="chip"><b>2</b> jumper wires</span>
      <span class="chip"><b>GND</b> pour</span>
    </div>
    <div class="dl">
      <a class="btn" id="dl" download="node_report.pdf" href="#">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
          stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12"/><path d="m7 10 5 5 5-5"/>
          <path d="M5 21h14"/></svg>
        Download node_report.pdf
      </a>
      <span class="meta">PDF · 4 pages · {kb}&nbsp;KB</span>
    </div>
    <div class="note">
      <span class="k">Before<br>milling</span>
      <p>Print <b>page&nbsp;4</b> at 100&#37; / &ldquo;actual size&rdquo; and caliper the red scale bar —
      it must read <b>50.0&nbsp;mm</b>. Then lay the real modules on the pads to confirm fit,
      and run a drill-only test cut before isolation routing.</p>
    </div>
  </div>

  <div class="card preview">
    <div class="bar"><span>Preview — node_report.pdf</span><span>pages 1–4</span></div>
    <iframe id="viewer" title="node_report.pdf preview"></iframe>
  </div>

  <footer>generated from pcb/gen_pdf.py · self-contained, no external assets</footer>
</div>
<script>
  const B64="{b64}";
  const bytes=Uint8Array.from(atob(B64),c=>c.charCodeAt(0));
  const url=URL.createObjectURL(new Blob([bytes],{{type:"application/pdf"}}));
  document.getElementById("viewer").src=url;
  const a=document.getElementById("dl");
  a.href="data:application/pdf;base64,"+B64;   // data URI so the download works offline
</script>'''

out=os.path.join(OUT,'report_download.html')
open(out,'w').write(HEAD+"\n"+BODY)
print('wrote',out,f'({os.path.getsize(out)//1024} KB, pdf {kb} KB)')
