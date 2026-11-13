"""Scaffold de automação a partir de uma spec em Markdown (specs/*.md). Primeiro passo do agent-qa-lynn.

  python test/scripts/qa_scaffold.py test/specs/feedback-resposta.md   # valida e mostra o plano (não escreve)
  python test/scripts/qa_scaffold.py test/specs/feedback-resposta.md --write  # gera features + plano em test/reports/scaffold/

O que faz:
  1. Valida a spec (front matter, regras RNxx com camadas, critérios de aceite em Gherkin).
  2. Converte cada bloco ```gherkin em cenário, com rastreabilidade (@ID-RNxx + riscos @Rxx).
  3. Casa cada passo com o catálogo: diz o que REUTILIZAR e o que CRIAR (com padrão sugerido).
  4. Lista data-testid da spec que ainda não existem em Page Objects.
  5. Monta o plano por camada da pirâmide para as regras sem critério de aceite.
Nunca sobrescreve uma feature existente sem --force.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # test/ (qa_support)
from qa_support.paths import ROOT, bootstrap  # noqa: E402

bootstrap()
from qa_support.paths import FEATURES, PAGES, REPORTS, UNIT  # noqa: E402
from qa_support.reporting.traceability import parse_spec  # noqa: E402
from qa_support.steps_index import find, iter_gherkin_steps, load_steps, suggest_pattern  # noqa: E402

GHERKIN_BLOCK = re.compile(r"```gherkin\s*\n(.*?)```", re.S)
REQUIRED_SECTIONS = ("## Contexto", "## Regras de negócio")
LAYER_HINT = {
    "unit": "regra pura em app/lynn_mock/domain → teste em test/unit com @pytest.mark.trace",
    "api": "cenário em test/features/api com steps httpx (reutilize o catálogo)",
    "ui": "cenário em test/features/ui; seletores data-testid só em test/features/pages",
}


def slugify(text: str) -> str:
    import unicodedata
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def validate(text: str, spec) -> list[str]:
    problems = [f"seção obrigatória ausente: '{s}'" for s in REQUIRED_SECTIONS if s not in text]
    if not re.match(r"^---\s*\n", text):
        problems.append("front matter (--- id/titulo/area/status ---) ausente")
    if not re.fullmatch(r"[A-Z]{3,6}", spec.id or ""):
        problems.append(f"id inválido '{spec.id}': use 3 a 6 letras maiúsculas")
    if spec.status != "pronta":
        problems.append(f"status '{spec.status}': o agente só gera automação para specs com status: pronta")
    if not spec.rules:
        problems.append("nenhuma regra no formato '- **RN01** — texto [camadas: ...] [riscos: ...]'")
    ids = [r.rid for r in spec.rules]
    problems += [f"regra duplicada: {x}" for x in sorted({x for x in ids if ids.count(x) > 1})]
    problems += [f"{r.rid} sem [camadas: ...]: a camada da pirâmide precisa ser decidida" for r in spec.rules if not r.layers]
    bad_layers = {l for r in spec.rules for l in r.layers} - set(LAYER_HINT)
    problems += [f"camada desconhecida: {l} (use unit, api, ui)" for l in sorted(bad_layers)]
    return problems


def parse_blocks(text: str, spec) -> list[dict]:
    """Cada bloco gherkin: tags (@RN01, @ui...), título, linhas. Tags @RNxx viram @ID-RNxx + riscos."""
    rules = {r.rid: r for r in spec.rules}
    blocks = []
    for raw in GHERKIN_BLOCK.findall(text):
        lines = [l.rstrip() for l in raw.strip().splitlines()]
        tags = [t for l in lines if l.strip().startswith("@") for t in l.split()]
        body = [l for l in lines if not l.strip().startswith("@")]
        title = next((l.split(":", 1)[1].strip() for l in body if re.match(r"\s*(Esquema do )?Cenário:", l)), "")
        rids = [t[1:] for t in tags if re.fullmatch(r"@RN\d+", t)]
        unknown = [r for r in rids if r not in rules]
        trace = [f"@{spec.id}-{r}" for r in rids] + sorted({f"@{risk}" for r in rids if r in rules for risk in rules[r].risks})
        other = [t for t in tags if not re.fullmatch(r"@RN\d+", t)]
        blocks.append({"title": title, "rids": rids, "unknown": unknown, "tags": other + trace, "body": body,
                       "ui": "@ui" in other})
    return blocks


def render_feature(spec, blocks: list[dict], layer: str) -> str:
    area_tag = "@ui" if layer == "ui" else "@api"
    head = ["# language: pt", f"# Gerado por test/scripts/qa_scaffold.py a partir de {Path(spec.path).name}.",
            "# Revise, complete os passos novos e rode. Rastreabilidade: @ID-RNxx (regras) e @Rxx (riscos).",
            f"{area_tag} @{spec.id.lower()}", f"Funcionalidade: {spec.title}" + (" (interface)" if layer == "ui" else ""),
            f"  Spec: test/specs/{Path(spec.path).name}"]
    for r in spec.rules:
        head.append(f"  {r.rid} — {r.text}")
    out = head + ["", "  Contexto:", "    Dado que a API de conversas está disponível", ""]
    for b in blocks:
        tags = [t for t in b["tags"] if t != area_tag]
        out.append("  " + " ".join(tags))
        for line in b["body"]:
            stripped = line.strip()
            if stripped.startswith("Dado que a API de conversas está disponível"):
                continue  # já está no Contexto
            indent = "  " if re.match(r"(Esquema do )?Cenário:|Exemplos:", stripped) else "    "
            if stripped.startswith("|"):
                indent = "      "
            out.append(indent + stripped if stripped else "")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def next_feature_path(area: str, spec) -> Path:
    folder = FEATURES / area
    existing = [p for p in folder.glob("*.feature")] if folder.exists() else []
    for p in existing:  # reaproveita o arquivo da mesma spec (regeração)
        if f"a partir de {Path(spec.path).name}" in p.read_text(encoding="utf-8"):
            return p
    numbers = [int(m.group(1)) for p in existing if (m := re.match(r"(\d+)_", p.name))]
    prefix = f"{max(numbers, default=0) + 1:02d}_" if area != "ui" else ""
    return folder / f"{prefix}{slugify(spec.title)}.feature"


def existing_automation(spec) -> dict[str, dict[str, int]]:
    """Quantos casos já carregam a tag de cada regra, por camada (evita duplicar automação)."""
    found = {r.rid: {"unit": 0, "api": 0, "ui": 0} for r in spec.rules}
    for f in FEATURES.glob("*/*.feature"):
        layer = "ui" if f.parent.name == "ui" else "api"
        txt = f.read_text(encoding="utf-8")
        for rid in found:
            found[rid][layer] += len(re.findall(rf"@{spec.id}-{rid}\b", txt))
    for f in UNIT.glob("test_*.py"):
        txt = f.read_text(encoding="utf-8")
        for rid in found:
            found[rid]["unit"] += len(re.findall(rf"[\"']{spec.id}-{rid}[\"']", txt))
    return found


def missing_testids(text: str) -> list[str]:
    section = text.split("## Telas", 1)[1].split("\n## ", 1)[0] if "## Telas" in text else ""
    wanted = set(re.findall(r"`([a-z0-9-]+)`", section))
    pages = "\n".join(p.read_text(encoding="utf-8") for p in PAGES.glob("*.py"))
    return sorted(t for t in wanted if f'"{t}"' not in pages and f"'{t}'" not in pages)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--write", action="store_true", help="grava as features e o plano")
    ap.add_argument("--force", action="store_true", help="sobrescreve a feature gerada anteriormente")
    args = ap.parse_args()
    spec_path = Path(args.spec).resolve()
    text = spec_path.read_text(encoding="utf-8")
    spec = parse_spec(spec_path)
    spec.path = spec_path.relative_to(ROOT).as_posix() if spec_path.is_relative_to(ROOT) else str(spec_path)
    area = re.search(r"^area:\s*(\w+)", text, re.M)
    area = area.group(1) if area else "api"

    problems = validate(text, spec)
    blocks = parse_blocks(text, spec)
    problems += [f"critério '{b['title']}' referencia regra inexistente: {', '.join(b['unknown'])}" for b in blocks if b["unknown"]]
    problems += [f"critério '{b['title']}' sem tag @RNxx: não há rastreabilidade" for b in blocks if not b["rids"]]

    steps = load_steps()
    reuse, create = [], {}
    for b in blocks:
        for line, word, kind, step_text in iter_gherkin_steps("\n".join(b["body"])):
            hit = find(steps, kind, step_text)
            if hit:
                reuse.append(f"`{word} {step_text}` → `{hit.func}` ({hit.file})")
            else:
                create.setdefault((kind, suggest_pattern(step_text)), []).append(f"{word} {step_text}")

    covered = {r for b in blocks for r in b["rids"]}
    plan = [f"# Plano de automação — {spec.id} · {spec.title}", "", f"Spec: `{spec.path}`", ""]
    plan += ["## Validação da spec", ""] + ([f"- ❌ {p}" for p in problems] or ["- ✅ estrutura válida"]) + [""]
    done = existing_automation(spec)

    def automated(rid, wanted):
        cells = [f"{l}:{done[rid][l]}" + ("" if done[rid][l] or l not in wanted else " ⚠") for l in ("unit", "api", "ui")]
        return " · ".join(cells)

    plan += ["## Regras × camadas da pirâmide", "",
             "| Regra | Camadas sugeridas | Riscos | Critério na spec | Já automatizado (tags) |", "|---|---|---|---|---|"]
    plan += [f"| {r.rid} — {r.text} | {', '.join(r.layers) or '—'} | {', '.join(r.risks) or '—'} | "
             f"{'sim' if r.rid in covered else 'não'} | {automated(r.rid, r.layers)} |" for r in spec.rules]
    plan += ["", "⚠ = camada sugerida na spec ainda sem nenhum caso com a tag da regra.", ""]
    plan += ["", "## Trabalho por camada", ""]
    for layer in ("unit", "api", "ui"):
        rs = [r.rid for r in spec.rules if layer in r.layers]
        if rs:
            plan.append(f"- **{layer}** ({', '.join(rs)}): {LAYER_HINT[layer]}")
    plan += ["", f"## Passos a CRIAR ({len(create)})", ""]
    plan += [f"- `{k}` → padrão sugerido: `{p}`  \n  usado em: {'; '.join(sorted(set(v))[:3])}" for (k, p), v in create.items()] or ["- nenhum"]
    plan += ["", f"## Passos REUTILIZADOS ({len(reuse)})", ""] + [f"- {r}" for r in sorted(set(reuse))] + [""]
    ids = missing_testids(text)
    plan += ["## data-testid sem Page Object", ""] + ([f"- `{t}`" for t in ids] or ["- nenhum"]) + [""]

    written = []
    if args.write and not problems:
        for layer, group in (("api", [b for b in blocks if not b["ui"]]), ("ui", [b for b in blocks if b["ui"]])):
            if not group:
                continue
            target = next_feature_path("ui" if layer == "ui" else area, spec)
            if target.exists() and not args.force and "qa_scaffold.py" not in target.read_text(encoding="utf-8"):
                print(f"✋ {target.relative_to(ROOT)} existe e não foi gerado pelo scaffold; nada escrito.")
                continue
            if target.exists() and not args.force:
                print(f"✋ {target.relative_to(ROOT)} já existe (use --force para regerar).")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(render_feature(spec, group, layer), encoding="utf-8")
            written.append(target.relative_to(ROOT).as_posix())
        out = REPORTS / "scaffold" / f"{spec.id}-plano.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(plan + ["## Arquivos gerados", ""] + [f"- `{w}`" for w in written]) + "\n", encoding="utf-8")
        written.append(out.relative_to(ROOT).as_posix())

    print("\n".join(plan))
    if written:
        print("Gerado:\n" + "\n".join(f"  - {w}" for w in written))
    if problems:
        print("\nSpec com problemas: corrija antes de gerar (nada foi escrito).", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
