"""report.html: resultado da execução (cucumber.json + unitários), com filtros e detalhes por passo."""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from .cucumber import scenario_status
from .html_common import esc, findings_table, meta_block, page, segmented_bar, status_chip


def _fmt_secs(s: float) -> str:
    return f"{s:.2f}s" if s < 60 else f"{int(s // 60)}m{s % 60:02.0f}s"


def _layer_of(feature: dict) -> str:
    return "ui" if "/ui/" in feature["uri"] or any(t["name"] == "@ui" for t in feature["tags"]) else "api"


def _steps_table(element: dict) -> str:
    rows = []
    for st in element["steps"]:
        res = st["result"]
        rows.append(f'<tr><td>{status_chip(res["status"], "")}</td><td><b>{esc(st["keyword"].strip())}</b> {esc(st["name"])}'
                    + ("".join(f'<div class="muted"><code>| {" | ".join(map(esc, r["cells"]))} |</code></div>'
                               for r in st.get("rows", [])))
                    + (f'<pre>{esc(res["error_message"])}</pre>' if res.get("error_message") else "")
                    + f'</td><td class="num">{res.get("duration", 0) / 1e9:.3f}s</td></tr>')
        for emb in st.get("embeddings", []):
            if emb.get("mime_type", "").startswith("image/"):
                rows.append(f'<tr><td></td><td colspan="2"><img loading="lazy" alt="screenshot do cenário" '
                            f'style="max-width:100%;border:1px solid var(--border);border-radius:8px" '
                            f'src="data:{esc(emb["mime_type"])};base64,{emb["data"]}"></td></tr>')
    return f'<table><thead><tr><th style="width:40px"></th><th>Passo</th><th class="num">Tempo</th></tr></thead><tbody>{"".join(rows)}</tbody></table>'


def render_report(cucumber: list[dict], unit: dict | None, meta: dict, sec: dict | None = None,
                  findings: list[dict] | None = None) -> str:
    scenarios, feature_rows, feature_blocks = [], [], []
    for f in cucumber:
        layer = _layer_of(f)
        counts, blocks = Counter(), []
        for el in f["elements"]:
            st = scenario_status(el)
            counts[st] += 1
            dur = sum(s["result"].get("duration", 0) for s in el["steps"]) / 1e9
            tags = [t["name"] for t in f["tags"] + el["tags"]]
            scenarios.append((st, dur))
            search = esc(" ".join([el["name"], f["name"], *tags]).lower())
            blocks.append(
                f'<details class="sc" data-status="{st}" data-layer="{layer}" data-search="{search}" {"open" if st == "failed" else ""}>'
                f'<summary>{status_chip(st, "")} {esc(el["name"])} <span class="muted">· {_fmt_secs(dur)}</span>'
                f'<div>{"".join(f"<span class=tag>{esc(t)}</span>" for t in tags)}</div></summary>'
                f'<div style="margin:10px 0 6px 26px">{_steps_table(el)}</div></details>')
        total = sum(counts.values())
        feature_rows.append(
            f'<tr><td><b>{esc(f["name"])}</b><div class="muted"><code>{esc(f["uri"])}</code></div></td><td>{layer.upper()}</td>'
            f'<td style="width:38%">{segmented_bar(counts, total, f["name"])}</td>'
            f'<td class="num">{counts["passed"]}/{total}</td><td class="num">{counts["failed"] or ""}</td></tr>')
        feature_blocks.append(
            f'<details class="feat card" data-layer="{layer}" {"open" if counts["failed"] else ""}>'
            f'<summary><h3 style="display:inline">{esc(f["name"])}</h3> <span class="muted">· {layer.upper()} · '
            f'{counts["passed"]}/{total} aprovados</span></summary><div style="margin-top:10px">{"".join(blocks)}</div></details>')

    unit_tests = (unit or {}).get("tests", [])
    sec_tests = (sec or {}).get("tests", [])
    unit_counts = Counter(t["status"] for t in unit_tests)
    sec_counts = Counter(t["status"] for t in sec_tests)
    bdd_counts = Counter(s for s, _ in scenarios)
    all_counts = bdd_counts + unit_counts + sec_counts
    total_all = sum(all_counts.values())
    duration = sum(d for _, d in scenarios) + sum(t["duration_s"] for t in unit_tests + sec_tests)
    executed = total_all - all_counts["xfailed"]  # achado conhecido não entra na taxa (nem a favor, nem contra)
    rate = (all_counts["passed"] / executed) if executed else 0
    open_findings = [f for f in (findings or []) if f["status"] != "mitigado"]

    unit_rows = "".join(
        f'<tr class="ut" data-status="{t["status"]}" data-layer="unit" data-search="{esc((t["name"] + " " + " ".join(t["tags"])).lower())}">'
        f'<td>{status_chip(t["status"], "")}</td><td><code>{esc(Path(t["file"]).name)}</code></td><td>{esc(t["name"])}'
        + (f'<pre>{esc(t["error"])}</pre>' if t.get("error") else "")
        + f'</td><td>{"".join(f"<span class=tag>@{esc(x)}</span>" for x in t["tags"])}</td><td class="num">{t["duration_s"]:.3f}s</td></tr>'
        for t in unit_tests)

    def _test_rows(tests, layer):
        return "".join(
            f'<tr class="ut" data-status="{t["status"]}" data-layer="{layer}" data-search="{esc((t["name"] + " " + " ".join(t["tags"])).lower())}">'
            f'<td>{status_chip(t["status"], "")}</td><td><code>{esc(Path(t["file"]).name)}</code></td><td>{esc(t["name"])}'
            + (f'<pre>{esc(t["error"])}</pre>' if t.get("error") else "")
            + f'</td><td>{"".join(f"<span class=tag>@{esc(x)}</span>" for x in t["tags"])}</td><td class="num">{t["duration_s"]:.3f}s</td></tr>'
            for t in tests)

    sec_rows = _test_rows(sec_tests, "sec")
    body = f"""
<header class="top"><div><h1>Relatório de execução · LYNN QA</h1>
<div class="sub">Conversa com agente — pirâmide de testes (unitário · API · UI) + segurança (OWASP)</div>{meta_block(meta)}</div>
<div style="display:flex;gap:8px;align-items:center"><span class="badge">{esc(meta.get("env", ""))}</span>
<button class="theme-toggle" id="theme" type="button">Tema claro/escuro</button></div></header>

<section class="kpis" aria-label="Indicadores">
 <div class="kpi hero"><div class="label">Taxa de aprovação</div><div class="value">{rate:.1%}</div>
  <div class="hint">{all_counts["passed"]} de {executed} casos avaliados · {all_counts["xfailed"]} vulnerabilidade(s) conhecida(s) à parte</div></div>
 <div class="kpi"><div class="label">Cenários BDD (API + UI)</div><div class="value">{len(scenarios)}</div>
  <div class="hint">{len(cucumber)} features</div></div>
 <div class="kpi"><div class="label">Testes unitários</div><div class="value">{len(unit_tests)}</div></div>
 <div class="kpi"><div class="label">Segurança (OWASP)</div><div class="value">{len(sec_tests)}</div>
  <div class="hint">{status_chip("xfailed" if open_findings else "passed", f"{len(open_findings)} achado(s) aberto(s)")}</div></div>
 <div class="kpi"><div class="label">Falhas</div><div class="value">{all_counts["failed"]}</div>
  <div class="hint">{status_chip("failed" if all_counts["failed"] else "passed", "requer ação" if all_counts["failed"] else "nenhuma")}</div></div>
 <div class="kpi"><div class="label">Tempo somado</div><div class="value">{_fmt_secs(duration)}</div>
  <div class="hint">soma dos casos (os shards rodam em paralelo)</div></div>
</section>

<section class="card"><h2>Resultado geral</h2>{segmented_bar(all_counts, total_all, "Todos os casos")}
<div class="legend"><span><i style="background:var(--good)"></i>✔ aprovados {all_counts["passed"]}</span>
<span><i style="background:var(--critical)"></i>✘ falhas {all_counts["failed"]}</span>
<span><i style="background:var(--serious)"></i>⚠ vulnerabilidades conhecidas {all_counts["xfailed"]}</span>
<span><i style="background:var(--warning)"></i>⏭ ignorados {all_counts["skipped"]}</span></div>
<p class="sub" style="margin:8px 0 0">A taxa de aprovação desconsidera as vulnerabilidades conhecidas (xfail estrito): elas estão
documentadas em <code>test/sec/FINDINGS.md</code> e o teste quebra quando a correção entrar.</p></section>

<section class="card"><h2>Por feature</h2><table><thead><tr><th>Feature</th><th>Camada</th><th>Status</th>
<th class="num">Aprovados</th><th class="num">Falhas</th></tr></thead><tbody>{"".join(feature_rows)}</tbody></table></section>

<div class="filters" role="search"><b style="font-size:13px">Filtrar</b>
 <select id="fStatus" aria-label="Status"><option value="">Todos os status</option><option value="passed">✔ Aprovados</option>
  <option value="failed">✘ Falhas</option><option value="xfailed">⚠ Vulnerabilidades conhecidas</option>
  <option value="skipped">⏭ Ignorados</option></select>
 <select id="fLayer" aria-label="Camada"><option value="">Todas as camadas</option><option value="ui">UI</option>
  <option value="api">API</option><option value="unit">Unitário</option><option value="sec">Segurança</option></select>
 <input id="fText" type="search" placeholder="Buscar por nome ou tag (ex.: @CONV-RN09, @R02)" aria-label="Buscar">
 <span id="fCount" class="muted"></span></div>

<section id="bdd">{"".join(feature_blocks)}</section>
<section class="card feat" data-layer="sec"><h2>Segurança (pytest · OWASP API Top 10 2023 · OWASP LLM Top 10 2025)</h2>
<p class="sub">Suíte transversal gerada pelo agente <code>qa-sec</code> em <code>test/sec</code>. Fica fora da contagem da pirâmide.</p>
{findings_table(findings or [])}
<table style="margin-top:14px"><thead><tr><th style="width:40px"></th><th>Arquivo</th><th>Teste</th><th>OWASP · rastreabilidade</th><th class="num">Tempo</th></tr></thead>
<tbody>{sec_rows or '<tr><td colspan="5" class="muted">Sem resultados de segurança nesta execução.</td></tr>'}</tbody></table></section>
<section class="card feat" data-layer="unit"><h2>Testes unitários (pytest)</h2>
<table><thead><tr><th style="width:40px"></th><th>Arquivo</th><th>Teste</th><th>Rastreabilidade</th><th class="num">Tempo</th></tr></thead>
<tbody>{unit_rows or '<tr><td colspan="5" class="muted">Sem resultados unitários nesta execução.</td></tr>'}</tbody></table></section>
"""
    script = """
(function(){
 var s=document.getElementById('fStatus'),l=document.getElementById('fLayer'),t=document.getElementById('fText'),c=document.getElementById('fCount');
 function apply(){
  var sv=s.value,lv=l.value,tv=t.value.trim().toLowerCase(),shown=0,total=0;
  document.querySelectorAll('.sc,.ut').forEach(function(e){
    total++;var ok=(!sv||e.dataset.status===sv)&&(!lv||e.dataset.layer===lv)&&(!tv||e.dataset.search.indexOf(tv)>=0);
    e.style.display=ok?'':'none'; if(ok)shown++;});
  document.querySelectorAll('.feat').forEach(function(f){
    var vis=f.querySelectorAll('.sc:not([style*="none"]),.ut:not([style*="none"])').length;
    f.style.display=vis?'':'none'; if(vis&&(sv||tv)&&f.tagName==='DETAILS')f.open=true;});
  c.textContent=shown+' de '+total+' casos';
 }
 [s,l].forEach(function(x){x.addEventListener('change',apply)}); t.addEventListener('input',apply); apply();
})();"""
    return page(f"Relatório LYNN QA — {meta.get('env', '')}", body, script)
