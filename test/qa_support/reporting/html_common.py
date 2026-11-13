"""Base visual compartilhada dos relatórios: tokens de cor (claro/escuro), tipografia e tooltip.

Paleta: referência validada (categórica em ordem fixa; status reservado para estado, sempre com
ícone + rótulo). Arquivos HTML autocontidos: abrem offline, sem CDN.
"""
from __future__ import annotations

import html

STATUS_ICON = {"passed": "✔", "failed": "✘", "skipped": "⏭", "none": "—", "undefined": "?", "xfailed": "⚠"}
STATUS_LABEL = {"passed": "aprovado", "failed": "falhou", "skipped": "ignorado", "none": "sem teste",
                "undefined": "indefinido", "xfailed": "vulnerabilidade conhecida"}
SEVERITY_CLASS = {"Crítica": "failed", "Alta": "failed", "Média": "xfailed", "Baixa": "skipped", "Informativa": "none"}


def esc(value) -> str:
    return html.escape(str(value), quote=True)


CSS = """
.viz-root{color-scheme:light;
 --page:#f9f9f7;--surface-1:#fcfcfb;--text-primary:#0b0b0b;--text-secondary:#52514e;--muted:#898781;
 --grid:#e1e0d9;--axis:#c3c2b7;--border:rgba(11,11,11,.10);
 --series-1:#2a78d6;--series-2:#eb6834;--series-3:#1baf7a;--series-4:#eda100;
 --good:#0ca30c;--warning:#fab219;--serious:#ec835a;--critical:#d03b3b;--good-text:#006300;--critical-text:#b02a2a;
 --wash:rgba(42,120,214,.06)}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme="light"])) .viz-root{color-scheme:dark;
 --page:#0d0d0d;--surface-1:#1a1a19;--text-primary:#f0efec;--text-secondary:#c3c2b7;--muted:#898781;
 --grid:#2c2c2a;--axis:#383835;--border:rgba(255,255,255,.10);
 --series-1:#3987e5;--series-2:#d95926;--series-3:#199e70;--series-4:#c98500;--good-text:#0ca30c;--critical-text:#e66767;
 --wash:rgba(57,135,229,.10)}}
:root[data-theme="dark"] .viz-root{color-scheme:dark;
 --page:#0d0d0d;--surface-1:#1a1a19;--text-primary:#f0efec;--text-secondary:#c3c2b7;--muted:#898781;
 --grid:#2c2c2a;--axis:#383835;--border:rgba(255,255,255,.10);
 --series-1:#3987e5;--series-2:#d95926;--series-3:#199e70;--series-4:#c98500;--good-text:#0ca30c;--critical-text:#e66767;
 --wash:rgba(57,135,229,.10)}
*{box-sizing:border-box}
body{margin:0}
.viz-root{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;background:var(--page);color:var(--text-primary);
 min-height:100vh;padding:28px 32px 64px;line-height:1.45}
.wrap{max-width:1180px;margin:0 auto}
header.top{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;margin-bottom:20px}
h1{font-size:22px;margin:0 0 4px} h2{font-size:16px;margin:0 0 12px} h3{font-size:14px;margin:0}
.sub{color:var(--text-secondary);font-size:13px}
.meta{display:flex;gap:6px 18px;flex-wrap:wrap;color:var(--text-secondary);font-size:12.5px;margin-top:6px}
.meta b{color:var(--text-primary);font-weight:600}
.badge{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;font-weight:600;border:1px solid var(--border);
 background:var(--surface-1);text-transform:uppercase;letter-spacing:.04em}
.card{background:var(--surface-1);border:1px solid var(--border);border-radius:12px;padding:18px 20px;margin-bottom:16px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-bottom:16px}
.kpi{background:var(--surface-1);border:1px solid var(--border);border-radius:12px;padding:14px 16px}
.kpi .label{font-size:12px;color:var(--text-secondary)} .kpi .value{font-size:28px;font-weight:650;margin-top:2px}
.kpi .hint{font-size:12px;color:var(--muted);margin-top:2px}
.kpi.hero .value{font-size:48px;line-height:1.05}
.status{display:inline-flex;align-items:center;gap:5px;font-size:12.5px;font-weight:600;white-space:nowrap}
.status .ico{display:inline-grid;place-items:center;width:16px;height:16px;border-radius:50%;color:#fff;font-size:10px}
.status.passed .ico{background:var(--good)} .status.failed .ico{background:var(--critical)}
.status.skipped .ico,.status.undefined .ico{background:var(--warning);color:#0b0b0b}
.status.xfailed .ico{background:var(--serious)} .status.xfailed{color:var(--text-primary)}
.status.none .ico{background:var(--axis);color:var(--text-primary)}
.status.passed{color:var(--good-text)} .status.failed{color:var(--critical-text)} .status.skipped,.status.none{color:var(--text-secondary)}
.seg{display:flex;gap:2px;height:14px;border-radius:4px;overflow:hidden;background:var(--grid)}
.seg span{display:block;height:100%} .seg .passed{background:var(--good)} .seg .failed{background:var(--critical)}
.seg .skipped{background:var(--warning)} .seg .xfailed{background:var(--serious)}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:12.5px;color:var(--text-secondary);margin-top:8px}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px;vertical-align:-1px}
table{border-collapse:collapse;width:100%;font-size:13px}
th{text-align:left;font-weight:600;color:var(--text-secondary);font-size:12px;border-bottom:1px solid var(--axis);padding:8px 10px}
td{border-bottom:1px solid var(--grid);padding:8px 10px;vertical-align:top}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
tr:hover td{background:var(--wash)}
code,pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12px}
pre{white-space:pre-wrap;background:var(--page);border:1px solid var(--border);border-radius:8px;padding:10px;max-height:320px;overflow:auto}
.tag{display:inline-block;font-size:11px;color:var(--text-secondary);border:1px solid var(--border);border-radius:6px;padding:0 6px;margin:2px 4px 0 0}
.filters{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:14px}
.filters select,.filters input{font:inherit;font-size:13px;padding:6px 10px;border-radius:8px;border:1px solid var(--border);
 background:var(--surface-1);color:var(--text-primary)}
.filters input{min-width:240px}
.theme-toggle{font:inherit;font-size:12px;padding:5px 10px;border-radius:8px;border:1px solid var(--border);background:var(--surface-1);
 color:var(--text-primary);cursor:pointer}
#tip{position:fixed;pointer-events:none;z-index:10;background:var(--surface-1);color:var(--text-primary);border:1px solid var(--border);
 border-radius:8px;padding:7px 10px;font-size:12.5px;box-shadow:0 4px 18px rgba(0,0,0,.15);opacity:0;transition:opacity .08s;max-width:340px}
.muted{color:var(--muted)} .right{text-align:right}
"""

SCRIPT = """
(function(){
  var tip=document.getElementById('tip');
  document.addEventListener('mousemove',function(e){
    var t=e.target.closest('[data-tip]');
    if(!t){tip.style.opacity=0;return}
    tip.innerHTML=t.getAttribute('data-tip');tip.style.opacity=1;
    var x=e.clientX+14,y=e.clientY+14,r=tip.getBoundingClientRect();
    if(x+r.width>innerWidth-8)x=e.clientX-r.width-14; if(y+r.height>innerHeight-8)y=e.clientY-r.height-14;
    tip.style.left=x+'px';tip.style.top=y+'px';
  });
  var btn=document.getElementById('theme');
  if(btn)btn.addEventListener('click',function(){
    var cur=document.documentElement.getAttribute('data-theme');
    var dark=cur?cur==='dark':matchMedia('(prefers-color-scheme: dark)').matches;
    document.documentElement.setAttribute('data-theme',dark?'light':'dark');
  });
})();
"""


def page(title: str, body: str, extra_script: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><style>{CSS}</style></head>
<body><div class="viz-root"><div class="wrap">{body}</div><div id="tip" role="tooltip"></div></div>
<script>{SCRIPT}{extra_script}</script></body></html>"""


def status_chip(status: str, text: str | None = None) -> str:
    return (f'<span class="status {esc(status)}"><span class="ico" aria-hidden="true">{STATUS_ICON.get(status, "?")}</span>'
            f'{esc(text if text is not None else STATUS_LABEL.get(status, status))}</span>')


def meta_block(meta: dict) -> str:
    items = [("Ambiente", meta.get("env")), ("Gerado em", meta.get("generated_at")), ("Commit", meta.get("commit")),
             ("Branch", meta.get("ref")), ("Alvo", meta.get("base_url"))]
    parts = [f"<span>{k}: <b>{esc(v)}</b></span>" for k, v in items if v]
    if meta.get("run_url"):
        parts.append(f'<span><a href="{esc(meta["run_url"])}">execução no GitHub Actions</a></span>')
    return f'<div class="meta">{"".join(parts)}</div>'


def segmented_bar(counts: dict, total: int, label: str = "") -> str:
    """Barra segmentada de status (aprovado/falhou/ignorado) com tooltip por segmento."""
    if not total:
        return '<div class="seg"></div>'
    segs = []
    for key in ("passed", "failed", "xfailed", "skipped"):
        n = counts.get(key, 0)
        if n:
            tip = f"<b>{esc(label)}</b><br>{STATUS_ICON[key]} {STATUS_LABEL[key]}: {n} de {total} ({n / total:.0%})"
            segs.append(f'<span class="{key}" style="flex:{n}" data-tip="{esc(tip)}"></span>')
    return f'<div class="seg" role="img" aria-label="{esc(label)}: {counts.get("passed", 0)} aprovados, ' \
           f'{counts.get("failed", 0)} falhas, {counts.get("skipped", 0)} ignorados">{"".join(segs)}</div>'


def severity_chip(severity: str) -> str:
    return status_chip(SEVERITY_CLASS.get(severity, "none"), severity)


def findings_table(findings: list[dict]) -> str:
    if not findings:
        return '<p class="sub">Nenhum achado registrado em <code>test/sec/FINDINGS.md</code>.</p>'
    rows = "".join(
        f'<tr><td><b>{esc(f["id"])}</b></td><td>{severity_chip(f["severity"])}</td><td class="num">{f["cvss"]:.1f}</td>'
        f'<td>{esc(f["owasp"])}</td><td>{esc(f["title"])}</td><td>{esc(f["risk"])}</td><td>{esc(f["status"])}</td></tr>'
        for f in sorted(findings, key=lambda f: -f["cvss"]))
    return ('<table><thead><tr><th>ID</th><th>Severidade</th><th class="num">CVSS</th><th>OWASP</th><th>Achado</th>'
            f'<th>Risco</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table>')
