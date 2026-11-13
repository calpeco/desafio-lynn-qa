"""cobertura.html: pirâmide de testes + cobertura de regras de negócio e riscos por camada."""
from __future__ import annotations

import re
from collections import Counter

from .html_common import esc, meta_block, page, status_chip
from .html_common import findings_table
from .traceability import ALL_LAYERS, LAYER_LABEL, LAYERS

# Identidade de camada = cor categórica em ordem fixa (base = slot 1).
LAYER_COLOR = {"unit": "var(--series-1)", "api": "var(--series-2)", "ui": "var(--series-3)", "sec": "var(--series-4)"}
_OWASP = re.compile(r"^(API|LLM)\d+:\d{4}$")
_TRACE = re.compile(r"(^R\d+$)|(-RN\d+$)")
LAYER_TOOL = {"unit": "pytest", "api": "behave + httpx", "ui": "behave + Playwright"}


def _pyramid_svg(stats: dict) -> str:
    W, row_h, gap, top = 760, 62, 10, 16
    bar_x0, bar_w = 190, 380
    cx = bar_x0 + bar_w / 2
    maxc = max((stats[l]["count"] for l in LAYERS), default=1) or 1
    height = top * 2 + 3 * row_h + 2 * gap
    parts = [f'<svg viewBox="0 0 {W} {height}" width="100%" role="img" aria-labelledby="pyrT pyrD" style="max-width:{W}px">',
             '<title id="pyrT">Pirâmide de testes</title>',
             f'<desc id="pyrD">{"; ".join(f"{LAYER_LABEL[l]}: {stats[l]['count']} casos" for l in LAYERS)}</desc>']
    # pirâmide ideal (referência) tracejada
    base_y = top + 3 * row_h + 2 * gap
    parts.append(f'<polygon points="{cx},{top - 6} {bar_x0},{base_y} {bar_x0 + bar_w},{base_y}" fill="none" '
                 f'stroke="var(--axis)" stroke-width="1.5" stroke-dasharray="5 5"/>')
    for i, layer in enumerate(LAYERS):  # ui (topo) → unit (base)
        s = stats[layer]
        y = top + i * (row_h + gap)
        w = max(bar_w * s["count"] / maxc, 6 if s["count"] else 0)
        x = cx - w / 2
        tip = (f"<b>{esc(LAYER_LABEL[layer])}</b> ({LAYER_TOOL[layer]})<br>{s['count']} casos · "
               f"{s['passed']} ✔ · {s['failed']} ✘<br>regras cobertas: {s['rules']}/{s['rules_total']}")
        parts.append(f'<g data-tip="{esc(tip)}" style="cursor:default">')
        parts.append(f'<rect x="{bar_x0 - 190}" y="{y}" width="{W}" height="{row_h}" fill="transparent"/>')  # alvo de hover
        if w:
            parts.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{row_h}" rx="4" fill="{LAYER_COLOR[layer]}"/>')
        label_inside = w > 120
        tx, anchor, fill = (cx, "middle", "#ffffff") if label_inside else (cx + w / 2 + 10, "start", "var(--text-primary)")
        parts.append(f'<text x="{tx:.1f}" y="{y + row_h / 2 + 6}" text-anchor="{anchor}" font-size="18" font-weight="650" '
                     f'fill="{fill}">{s["count"]}</text>')
        parts.append(f'<text x="0" y="{y + row_h / 2 - 3}" font-size="14" font-weight="600" fill="var(--text-primary)">'
                     f'{esc(LAYER_LABEL[layer])}</text>')
        parts.append(f'<text x="0" y="{y + row_h / 2 + 15}" font-size="12" fill="var(--text-secondary)">{LAYER_TOOL[layer]}</text>')
        rate = f"{s['passed'] / s['count']:.0%}" if s["count"] else "—"
        icon = "✘" if s["failed"] else ("✔" if s["count"] else "—")
        parts.append(f'<text x="{bar_x0 + bar_w + 24}" y="{y + row_h / 2 - 3}" font-size="13" fill="var(--text-primary)">'
                     f'{icon} {rate} aprovados</text>')
        parts.append(f'<text x="{bar_x0 + bar_w + 24}" y="{y + row_h / 2 + 15}" font-size="12" fill="var(--text-secondary)">'
                     f'regras cobertas {s["rules"]}/{s["rules_total"]}</text>')
        parts.append("</g>")
    parts.append("</svg>")
    return "".join(parts)


# Critério de pirâmide saudável (explícito e versionado): a base precisa ser claramente maior.
RATIO_UNIT_API = 1.5   # unitário ≥ 1,5 × API
RATIO_API_UI = 2.0     # API ≥ 2 × UI


def _shape_verdict(stats: dict) -> str:
    u, a, i = (stats[l]["count"] for l in ("unit", "api", "ui"))
    criterio = f"critério: unitário ≥ {RATIO_UNIT_API:g}× API e API ≥ {RATIO_API_UI:g}× UI"
    if i > a or i > u:
        return status_chip("failed", f"Pirâmide invertida (casquinha de sorvete): topo maior que as camadas de baixo · {criterio}")
    if u >= RATIO_UNIT_API * a and a >= RATIO_API_UI * i:
        return status_chip("passed", f"Pirâmide saudável: unitário {u / max(a, 1):.1f}× API · API {a / max(i, 1):.1f}× UI ({criterio})")
    return status_chip("skipped", f"Pirâmide irregular: unitário {u / max(a, 1):.1f}× API · API {a / max(i, 1):.1f}× UI ({criterio})")


def _meter(pct: float, color: str, label: str, detail: str) -> str:
    return (f'<div style="display:grid;grid-template-columns:220px 1fr 170px;gap:12px;align-items:center;margin:8px 0" '
            f'data-tip="{esc(f"<b>{label}</b><br>{detail}")}"><span>{esc(label)}</span>'
            f'<div style="height:10px;border-radius:4px;background:var(--grid)"><div style="height:100%;width:{pct:.1f}%;'
            f'border-radius:4px;background:{color}"></div></div><span class="right" style="font-variant-numeric:tabular-nums">'
            f'<b>{pct:.0f}%</b> <span class="muted">{esc(detail)}</span></span></div>')


def _cell(cell: dict, suggested: bool) -> str:
    if cell["count"] == 0:
        return status_chip("skipped", "sugerida, sem teste") if suggested else '<span class="muted">—</span>'
    if cell["failed"]:
        return status_chip("failed", f'{cell["failed"]}/{cell["count"]} falham')
    return status_chip("passed", f'{cell["count"]}')


def render_coverage(cases, specs, matrix, risks, code_cov, meta, findings=None) -> str:
    total_rules = len(matrix) or 1
    stats = {}
    for layer in ALL_LAYERS:
        lc = [c for c in cases if c.layer == layer]
        cnt = Counter(c.status for c in lc)
        stats[layer] = {"count": len(lc), "passed": cnt["passed"], "failed": cnt["failed"], "xfailed": cnt["xfailed"],
                        "rules": sum(1 for r in matrix if r["per_layer"][layer]["count"]), "rules_total": len(matrix)}
    covered = sum(r["covered"] for r in matrix)
    total_cases = sum(stats[l]["count"] for l in LAYERS) or 1
    dist = " · ".join(f"{100 * stats[l]['count'] / total_cases:.0f}%" for l in ("unit", "api", "ui"))
    failing_rules = sum(r["failing"] for r in matrix)
    p1 = [r for r in risks if r["priority"] == "P1"]
    p1_cov = sum(1 for r in p1 if r["total"])
    traced = sum(1 for c in cases if any(_TRACE.search(t) for t in c.tags))

    meters = "".join(_meter(100 * stats[l]["rules"] / total_rules, LAYER_COLOR[l], LAYER_LABEL[l],
                            f'{stats[l]["rules"]}/{len(matrix)} regras') for l in ALL_LAYERS)

    rows = []
    for spec in specs:
        rows.append(f'<tr><td colspan="7" style="background:var(--page)"><b>{esc(spec.id)}</b> · {esc(spec.title)} '
                    f'<span class="muted"><code>{esc(spec.path)}</code></span></td></tr>')
        for r in (x for x in matrix if x["spec"] == spec.id):
            rule = r["rule"]
            cells = "".join(f'<td>{_cell(r["per_layer"][l], l in rule.layers)}</td>' for l in ALL_LAYERS)
            risks_txt = " ".join(f'<span class="tag">{esc(x)}</span>' for x in rule.risks)
            rows.append(f'<tr><td style="white-space:nowrap"><code>@{esc(rule.tag)}</code></td><td>{esc(rule.text)}<div>{risks_txt}</div></td>{cells}'
                        f'<td>{status_chip("failed" if r["failing"] else ("passed" if r["covered"] else "none"), "")}</td></tr>')

    risk_rows = []
    for r in sorted(risks, key=lambda x: (x["priority"], x["id"])):
        st = "failed" if r["failed"] else ("passed" if r["total"] else "none")
        cells = "".join(f'<td class="num">{r["per_layer"][l] or "—"}</td>' for l in ALL_LAYERS)
        risk_rows.append(f'<tr><td><b>{esc(r["id"])}</b></td><td>{esc(r["text"])}</td><td>{esc(r["priority"])}</td>'
                         f'<td class="num">{esc(r["score"])}</td>{cells}<td>{status_chip(st, "coberto" if st == "passed" else None)}</td></tr>')

    if code_cov:
        code = "".join(_meter(code_cov[l]["percent"], LAYER_COLOR[l], LAYER_LABEL[l],
                              f'{code_cov[l]["covered"]}/{code_cov[l]["statements"]} linhas')
                       for l in LAYERS if l in code_cov)
        code_html = f'<p class="sub">Linhas de <code>app/lynn_mock/</code> exercitadas por camada (coverage.py).</p>{code}'
    else:
        code_html = ('<p class="sub">Cobertura de código não coletada nesta execução. No CI, ela é medida com '
                     '<code>coverage.py</code> (<code>LYNN_COVERAGE=1</code>) e aparece aqui por camada.</p>')

    owasp = {}
    for c in (c for c in cases if c.layer == "sec"):
        for t in (t for t in c.tags if _OWASP.match(t)):
            owasp.setdefault(t, Counter())[c.status] += 1
    if owasp:
        orows = "".join(
            f'<tr><td><b>{esc(cat)}</b></td><td class="num">{sum(cnt.values())}</td><td class="num">{cnt["passed"]}</td>'
            f'<td class="num">{cnt["xfailed"] or "—"}</td><td class="num">{cnt["failed"] or "—"}</td>'
            f'<td>{status_chip("failed" if cnt["failed"] else ("xfailed" if cnt["xfailed"] else "passed"), "")}</td></tr>'
            for cat, cnt in sorted(owasp.items(), key=lambda kv: (kv[0][:3], int(kv[0][3:].split(":")[0]))))
        owasp_html = ('<table><thead><tr><th>Categoria</th><th class="num">Testes</th><th class="num">✔ Seguros</th>'
                      '<th class="num">⚠ Conhecidas</th><th class="num">✘ Falhas</th><th>Status</th></tr></thead>'
                      f'<tbody>{orows}</tbody></table>')
    else:
        owasp_html = '<p class="sub">Suíte de segurança não executada nesta rodada.</p>'
    body = f"""
<header class="top"><div><h1>Cobertura de testes · LYNN QA</h1>
<div class="sub">Pirâmide de testes e rastreabilidade: regra de negócio → risco → cenários por camada</div>{meta_block(meta)}</div>
<div style="display:flex;gap:8px;align-items:center"><span class="badge">{esc(meta.get("env", ""))}</span>
<button class="theme-toggle" id="theme" type="button">Tema claro/escuro</button></div></header>

<section class="kpis">
 <div class="kpi hero"><div class="label">Regras de negócio cobertas</div><div class="value">{covered / total_rules:.0%}</div>
  <div class="hint">{covered} de {len(matrix)} regras em {len(specs)} spec(s)</div></div>
 <div class="kpi"><div class="label">Distribuição da pirâmide</div><div class="value" style="font-size:22px;line-height:1.6">{dist}</div>
  <div class="hint">unitário · API · UI (alvo de mercado ≈ 70 · 20 · 10)</div></div>
 <div class="kpi"><div class="label">Riscos P1 cobertos</div><div class="value">{p1_cov}/{len(p1)}</div></div>
 <div class="kpi"><div class="label">Regras com falha</div><div class="value">{failing_rules}</div>
  <div class="hint">{status_chip("failed" if failing_rules else "passed", "requer ação" if failing_rules else "nenhuma")}</div></div>
 <div class="kpi"><div class="label">Casos rastreados</div><div class="value">{traced}/{len(cases)}</div>
  <div class="hint">com tag de regra (@SPEC-RNxx) ou risco (@Rxx)</div></div>
</section>

<section class="card"><h2>Pirâmide de testes</h2>
<p class="sub" style="margin-top:-6px">Largura proporcional ao número de casos. O contorno tracejado é a forma esperada. Segurança é transversal e não entra na pirâmide.</p>
{_pyramid_svg(stats)}
<div style="margin-top:6px">{_shape_verdict(stats)}</div></section>

<section class="card"><h2>Cobertura de regras de negócio por camada</h2>{meters}</section>

<section class="card"><h2>Matriz de rastreabilidade</h2>
<p class="sub" style="margin-top:-6px">Contagem de casos por camada. "Sugerida, sem teste" = a spec pede a camada e ainda não há teste nela.</p>
<table><thead><tr><th>Regra</th><th>Descrição · riscos</th><th>UI</th><th>API</th><th>Unitário</th><th>Segurança</th><th>Status</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></section>

<section class="card"><h2>Cobertura de riscos</h2>
<p class="sub" style="margin-top:-6px">Matriz de <code>docs/ESTRATEGIA_E_RISCOS.md</code>. Riscos sem caso automatizado precisam de justificativa na estratégia.</p>
<table><thead><tr><th>ID</th><th>Risco</th><th>Prior.</th><th class="num">Score</th><th class="num">UI</th><th class="num">API</th>
<th class="num">Unit</th><th class="num">Sec</th><th>Status</th></tr></thead><tbody>{"".join(risk_rows)}</tbody></table></section>

<section class="card"><h2>Segurança · OWASP</h2>
<p class="sub" style="margin-top:-6px">Suíte transversal <code>test/sec</code> (agente <code>qa-sec</code>), fora da contagem da pirâmide.
⚠ = teste que descreve o comportamento seguro e falha hoje: vulnerabilidade conhecida, com xfail estrito, em <code>test/sec/FINDINGS.md</code>.</p>
{owasp_html}
<h3 style="margin:16px 0 8px">Achados</h3>{findings_table(findings or [])}</section>

<section class="card"><h2>Cobertura de código</h2>{code_html}</section>
"""
    return page(f"Cobertura LYNN QA — {meta.get('env', '')}", body)
