"""sec-report.html: relatório dedicado de segurança (suíte test/sec, agente qa-sec).

Fontes (todas geradas ou mantidas no repositório):
  - test/reports/raw/sec-results.json   resultados da suíte (status, tags OWASP/trace, reason do xfail)
  - test/sec/FINDINGS.md                achados SEC-NNN (tabela-resumo + seções detalhadas)
  - test/sec/README.md                  modelo de ameaças e mapa OWASP (justificativas de N/A)
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path

from .html_common import esc, meta_block, page, segmented_bar, severity_chip, status_chip

SEVERITY_ORDER = ["Crítica", "Alta", "Média", "Baixa", "Informativa"]
SEVERITY_COLOR = {"Crítica": "var(--critical)", "Alta": "var(--critical)", "Média": "var(--serious)",
                  "Baixa": "var(--warning)", "Informativa": "var(--axis)"}

OWASP_API_2023 = {
    "API1": "Autorização quebrada em nível de objeto (BOLA)",
    "API2": "Autenticação quebrada",
    "API3": "Autorização quebrada em nível de propriedade",
    "API4": "Consumo irrestrito de recursos",
    "API5": "Autorização quebrada em nível de função",
    "API6": "Acesso irrestrito a fluxos de negócio sensíveis",
    "API7": "Server-Side Request Forgery (SSRF)",
    "API8": "Configuração de segurança incorreta",
    "API9": "Gestão inadequada de inventário",
    "API10": "Consumo inseguro de APIs",
}
OWASP_LLM_2025 = {
    "LLM01": "Prompt injection",
    "LLM02": "Divulgação de informação sensível",
    "LLM03": "Cadeia de suprimentos",
    "LLM04": "Envenenamento de dados e do modelo",
    "LLM05": "Tratamento impróprio da saída",
    "LLM06": "Agência excessiva",
    "LLM07": "Vazamento do prompt de sistema",
    "LLM08": "Fraquezas em vetores e embeddings",
    "LLM09": "Desinformação",
    "LLM10": "Consumo ilimitado",
}
_SEC_ID = re.compile(r"SEC-\d{3}")


# ------------------------------------------------------------------ Markdown mínimo (subconjunto do FINDINGS/README)
def _inline(text: str) -> str:
    out = esc(text)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", out)
    return re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', out)


def md_to_html(md: str) -> str:
    """Listas aninhadas (2 espaços por nível), blocos de código, tabelas, parágrafos e inline (code, bold, link)."""
    html, lines, i = [], md.splitlines(), 0
    list_depth = 0

    def close_lists(target=0):
        nonlocal list_depth
        while list_depth > target:
            html.append("</ul>")
            list_depth -= 1

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("```"):
            close_lists()
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("```"):
                j += 1
            indent = len(line) - len(line.lstrip())
            code = "\n".join(l[indent:] if len(l) >= indent else l for l in lines[i + 1:j])
            html.append(f"<pre>{esc(code)}</pre>")
            i = j + 1
            continue
        if stripped.startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            close_lists()
            head = [c.strip() for c in stripped.strip("|").split("|")]
            rows, j = [], i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
                j += 1
            html.append("<table><thead><tr>" + "".join(f"<th>{_inline(h)}</th>" for h in head) + "</tr></thead><tbody>"
                        + "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>" for r in rows)
                        + "</tbody></table>")
            i = j
            continue
        m = re.match(r"^(\s*)- (.*)$", line)
        if m:
            depth = len(m.group(1)) // 2 + 1
            while list_depth < depth:
                html.append("<ul>")
                list_depth += 1
            close_lists(depth)
            html.append(f"<li>{_inline(m.group(2))}</li>")
        elif stripped:
            close_lists()
            html.append(f"<p>{_inline(stripped)}</p>")
        else:
            close_lists()
        i += 1
    close_lists()
    return "\n".join(html)


# ------------------------------------------------------------------ leitura das fontes
def parse_finding_sections(findings_md: Path) -> dict[str, dict]:
    """### SEC-NNN · título  →  {id: {"title", "body_md"}}"""
    if not findings_md.exists():
        return {}
    text = findings_md.read_text(encoding="utf-8")
    sections = {}
    for block in re.split(r"(?m)^### ", text)[1:]:
        header, _, body = block.partition("\n")
        m = _SEC_ID.search(header)
        if m:
            title = header.split("·", 1)[-1].strip()
            sections[m.group(0)] = {"title": title, "body_md": body.strip().rstrip("-").strip()}
    return sections


def parse_owasp_map(readme_md: Path) -> dict[str, str]:
    """Categorias marcadas como N/A no mapa OWASP do README da suíte → justificativa."""
    na = {}
    if not readme_md.exists():
        return na
    for line in readme_md.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and cells[1] == "N/A":
            head = cells[0].split()[0]
            prefix = re.match(r"(API|LLM)", head)
            if not prefix:
                continue
            for num in re.findall(r"\d+", head):
                key = f"{prefix.group(1)}{int(num):02d}" if prefix.group(1) == "LLM" else f"API{int(num)}"
                na[key] = cells[2]
    return na


def threat_model_md(readme_md: Path) -> str:
    if not readme_md.exists():
        return ""
    text = readme_md.read_text(encoding="utf-8")
    m = re.search(r"## Modelo de ameaças.*?\n(.*?)(?=\n## )", text, re.S)
    return m.group(1).strip() if m else ""


# ------------------------------------------------------------------ render
def _sev_bars(findings: list[dict]) -> str:
    counts = Counter(f["severity"] for f in findings if f["status"] != "mitigado")
    top = max(counts.values(), default=1)
    rows = []
    for sev in SEVERITY_ORDER:
        n = counts.get(sev, 0)
        width = 100 * n / top if top else 0
        rows.append(
            f'<div style="display:grid;grid-template-columns:130px 1fr 40px;gap:12px;align-items:center;margin:7px 0" '
            f'data-tip="<b>{esc(sev)}</b><br>{n} achado(s) aberto(s)">'
            f'<span>{severity_chip(sev)}</span>'
            f'<div style="height:12px;background:var(--grid);border-radius:4px"><div style="height:100%;width:{width:.1f}%;'
            f'background:{SEVERITY_COLOR[sev]};border-radius:4px"></div></div>'
            f'<span class="right" style="font-variant-numeric:tabular-nums"><b>{n}</b></span></div>')
    return "".join(rows)


def _owasp_table(catalog: dict, year: str, by_cat: dict, na: dict, findings_by_cat: dict) -> str:
    rows = []
    for key, name in catalog.items():
        cat_id = f"{key}:{year}"
        cnt = by_cat.get(cat_id)
        nf = findings_by_cat.get(key, [])
        if cnt:
            st = "failed" if cnt["failed"] else ("xfailed" if cnt["xfailed"] else "passed")
            label = {"failed": "regressão", "xfailed": "vulnerável", "passed": "protegido"}[st]
            rows.append(f'<tr><td><b>{esc(key)}</b></td><td>{esc(name)}</td><td class="num">{sum(cnt.values())}</td>'
                        f'<td class="num">{cnt["passed"]}</td><td class="num">{cnt["xfailed"] or "—"}</td>'
                        f'<td class="num">{cnt["failed"] or "—"}</td><td>{", ".join(nf) or "—"}</td>'
                        f'<td>{status_chip(st, label)}</td></tr>')
        else:
            why = na.get(key)
            rows.append(f'<tr><td><b>{esc(key)}</b></td><td>{esc(name)}</td><td colspan="5" class="muted">'
                        f'{_inline(why) if why else "sem teste e sem justificativa registrada"}</td>'
                        f'<td>{status_chip("none", "não aplicável") if why else status_chip("skipped", "lacuna")}</td></tr>')
    return ('<table><thead><tr><th>ID</th><th>Categoria</th><th class="num">Testes</th><th class="num">✔ Protegidos</th>'
            '<th class="num">⚠ Vulneráveis</th><th class="num">✘ Regressões</th><th>Achados</th><th>Situação</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table>')


def render_sec_report(sec_results: dict | None, findings: list[dict], findings_md: Path, readme_md: Path,
                      meta: dict) -> str:
    tests = (sec_results or {}).get("tests", [])
    counts = Counter(t["status"] for t in tests)
    sections = parse_finding_sections(findings_md)
    na = parse_owasp_map(readme_md)
    open_findings = sorted((f for f in findings if f["status"] != "mitigado"), key=lambda f: -f["cvss"])
    worst = open_findings[0] if open_findings else None

    by_cat: dict[str, Counter] = defaultdict(Counter)
    for t in tests:
        for tag in t["tags"]:
            if re.match(r"^(API|LLM)\d+:\d{4}$", tag):
                by_cat[tag][t["status"]] += 1
    findings_by_cat: dict[str, list[str]] = defaultdict(list)
    for f in findings:
        for key in re.findall(r"(API\d+|LLM\d+)", f["owasp"]):
            findings_by_cat[key].append(f["id"])
    tests_by_finding: dict[str, list[dict]] = defaultdict(list)
    for t in tests:
        for sid in set(_SEC_ID.findall(t.get("error") or "")):
            tests_by_finding[sid].append(t)

    # ---------- fichas dos achados
    cards = []
    for f in sorted(findings, key=lambda f: -f["cvss"]):
        related = tests_by_finding.get(f["id"], [])
        if any(t["status"] == "failed" for t in related):
            repro = status_chip("failed", "XPASS: o comportamento seguro passou; confirme a correção e atualize o achado")
        elif related:
            repro = status_chip("xfailed", f"reproduzido nesta execução por {len(related)} teste(s)")
        else:
            repro = status_chip("none", "nenhum teste ligado a este achado foi executado")
        section = sections.get(f["id"], {})
        tests_html = "".join(f'<li>{status_chip(t["status"], "")} <code>{esc(t["id"])}</code></li>' for t in related)
        cards.append(
            f'<details class="card finding" id="{esc(f["id"])}" {"open" if f["severity"] in ("Crítica", "Alta") else ""}>'
            f'<summary><span style="display:inline-flex;gap:10px;align-items:center;flex-wrap:wrap">'
            f'<b style="font-size:15px">{esc(f["id"])}</b>{severity_chip(f["severity"])}'
            f'<span class="badge">CVSS {f["cvss"]:.1f}</span><span>{esc(f["title"])}</span></span>'
            f'<div style="margin-top:6px" class="sub">OWASP {esc(f["owasp"])} · risco {esc(f["risk"])} · status '
            f'<b>{esc(f["status"])}</b> · {repro}</div></summary>'
            f'<div class="finding-body">{md_to_html(section.get("body_md", "")) or "<p class=muted>Sem detalhamento.</p>"}'
            + (f'<h4>Testes que reproduzem</h4><ul class="plain">{tests_html}</ul>' if related else "")
            + "</div></details>")

    # ---------- todos os testes
    cats = sorted(by_cat, key=lambda c: (c[:3], int(re.findall(r"\d+", c)[0])))
    rows = "".join(
        f'<tr class="ut" data-status="{t["status"]}" data-cat="{esc(" ".join(x for x in t["tags"] if ":" in x))}" '
        f'data-search="{esc((t["name"] + " " + t["file"] + " " + " ".join(t["tags"]) + " " + (t.get("error") or "")).lower())}">'
        f'<td>{status_chip(t["status"], "")}</td><td><code>{esc(Path(t["file"]).stem)}</code></td><td>{esc(t["name"])}'
        + (f'<div class="muted" style="font-size:12px">{esc(t["error"][:220])}</div>' if t.get("error") else "")
        + f'</td><td>{"".join(f"<span class=tag>@{esc(x)}</span>" for x in t["tags"])}</td>'
        f'<td class="num">{t["duration_s"]:.3f}s</td></tr>' for t in tests)

    risk_label = worst["severity"] if worst else "Sem achados abertos"
    risk_status = {"Crítica": "failed", "Alta": "failed", "Média": "xfailed"}.get(risk_label, "passed" if not worst else "skipped")
    threat = md_to_html(threat_model_md(readme_md))

    body = f"""
<header class="top"><div><h1>Relatório de segurança · LYNN QA</h1>
<div class="sub">Suíte <code>test/sec</code> (agente <code>qa-sec</code>) · OWASP API Security Top 10 2023 · OWASP Top 10 para LLM 2025</div>
{meta_block(meta)}</div>
<div style="display:flex;gap:8px;align-items:center"><span class="badge">{esc(meta.get("env", ""))}</span>
<button class="theme-toggle" id="theme" type="button">Tema claro/escuro</button></div></header>

<section class="kpis">
 <div class="kpi hero"><div class="label">Risco atual (pior achado aberto)</div>
  <div class="value" style="font-size:40px">{esc(risk_label)}</div>
  <div class="hint">{status_chip(risk_status, f"{worst['id']} · CVSS {worst['cvss']:.1f}" if worst else "nenhum")}</div></div>
 <div class="kpi"><div class="label">Achados abertos</div><div class="value">{len(open_findings)}</div>
  <div class="hint">de {len(findings)} registrados em FINDINGS.md</div></div>
 <div class="kpi"><div class="label">Testes de segurança</div><div class="value">{len(tests)}</div>
  <div class="hint">{len(cats)} categorias OWASP exercitadas</div></div>
 <div class="kpi"><div class="label">Controles verificados</div><div class="value">{counts["passed"]}</div>
  <div class="hint">{status_chip("passed", "seguros")}</div></div>
 <div class="kpi"><div class="label">Regressões</div><div class="value">{counts["failed"]}</div>
  <div class="hint">{status_chip("failed" if counts["failed"] else "passed", "requer ação" if counts["failed"] else "nenhuma")}</div></div>
</section>

<section class="card" style="display:grid;grid-template-columns:1fr 1fr;gap:28px">
 <div><h2>Achados abertos por severidade</h2>{_sev_bars(findings)}
  <p class="sub" style="margin-top:10px">Severidade com CVSS 3.1 (vetor completo em cada ficha).</p></div>
 <div><h2>Resultado dos testes</h2>{segmented_bar(counts, len(tests), "Testes de segurança")}
  <div class="legend"><span><i style="background:var(--good)"></i>✔ protegido {counts["passed"]}</span>
  <span><i style="background:var(--serious)"></i>⚠ vulnerabilidade conhecida {counts["xfailed"]}</span>
  <span><i style="background:var(--critical)"></i>✘ regressão {counts["failed"]}</span></div>
  <p class="sub" style="margin-top:10px">⚠ = o teste descreve o comportamento <b>seguro</b> e falha hoje (xfail estrito).
  Quando a correção entrar, ele vira XPASS e reprova a pipeline, o que obriga a atualizar o achado.</p></div>
</section>

<section class="card"><h2>Cobertura OWASP API Security Top 10 (2023)</h2>
{_owasp_table(OWASP_API_2023, "2023", by_cat, na, findings_by_cat)}</section>
<section class="card"><h2>Cobertura OWASP Top 10 para aplicações LLM (2025)</h2>
{_owasp_table(OWASP_LLM_2025, "2025", by_cat, na, findings_by_cat)}</section>

<h2 style="margin:22px 0 10px">Achados (do mais grave ao menos grave)</h2>
{"".join(cards) or '<p class="sub">Nenhum achado registrado.</p>'}

<details class="card"><summary><h2 style="display:inline">Modelo de ameaças (STRIDE)</h2></summary>
<div class="finding-body">{threat or '<p class="muted">Não encontrado em test/sec/README.md.</p>'}</div></details>

<section class="card"><h2>Todos os testes</h2>
<div class="filters" role="search">
 <select id="fStatus" aria-label="Status"><option value="">Todos os status</option><option value="passed">✔ Protegido</option>
  <option value="xfailed">⚠ Vulnerabilidade conhecida</option><option value="failed">✘ Regressão</option></select>
 <select id="fCat" aria-label="Categoria OWASP"><option value="">Todas as categorias</option>
  {"".join(f'<option value="{esc(c)}">{esc(c)}</option>' for c in cats)}</select>
 <input id="fText" type="search" placeholder="Buscar por nome, arquivo, tag ou SEC-NNN" aria-label="Buscar">
 <span id="fCount" class="muted"></span></div>
<table><thead><tr><th style="width:40px"></th><th>Arquivo</th><th>Teste</th><th>OWASP · rastreabilidade</th><th class="num">Tempo</th></tr></thead>
<tbody>{rows or '<tr><td colspan="5" class="muted">Suíte de segurança não executada.</td></tr>'}</tbody></table></section>

<p class="sub">Escopo autorizado: somente a instância local ou um ambiente de teste da equipe, com payloads mínimos e
não destrutivos. Limites: com o LLM simulado, resistir a uma injeção não prova a robustez de um modelo real (ver
SEC-009). Não há DAST nem fuzzing amplo, TLS nem carga real.</p>
<style>.finding summary{{cursor:pointer;list-style:none}} .finding-body{{margin-top:12px;font-size:13.5px}}
.finding-body ul{{margin:4px 0 4px 18px;padding:0}} .finding-body li{{margin:3px 0}} .finding-body h4{{margin:14px 0 6px}}
ul.plain{{list-style:none;margin:0;padding:0}} ul.plain li{{margin:4px 0}}
.finding-body table{{margin:8px 0}}</style>
"""
    script = """
(function(){
 var s=document.getElementById('fStatus'),c=document.getElementById('fCat'),t=document.getElementById('fText'),n=document.getElementById('fCount');
 function apply(){var sv=s.value,cv=c.value,tv=t.value.trim().toLowerCase(),shown=0,total=0;
  document.querySelectorAll('tr.ut').forEach(function(e){total++;
   var ok=(!sv||e.dataset.status===sv)&&(!cv||e.dataset.cat.split(' ').indexOf(cv)>=0)&&(!tv||e.dataset.search.indexOf(tv)>=0);
   e.style.display=ok?'':'none'; if(ok)shown++;});
  n.textContent=shown+' de '+total+' testes';}
 [s,c].forEach(function(x){x.addEventListener('change',apply)}); t.addEventListener('input',apply); apply();
})();"""
    return page(f"Segurança LYNN QA — {meta.get('env', '')}", body, script)
