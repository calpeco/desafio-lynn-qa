"""Índice dos step definitions (via AST, sem executar o behave) e casamento de passos Gherkin.

Usado pelo catálogo (test/docs/STEP_CATALOG.md) e pelo scaffold do agent-qa-lynn para REUTILIZAR
passos existentes antes de criar novos. O casamento segue as regras do parse/behave usadas no
projeto: {x:Q} = texto entre aspas sem aspas internas, {n:d} = inteiro, {x} = qualquer texto.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

from .paths import ROOT, STEPS as STEPS_DIR
KEYWORDS = {"Dado": "given", "Dada": "given", "Dados": "given", "Dadas": "given", "Quando": "when",
            "Então": "then", "Entao": "then", "E": None, "Mas": None}
_TYPES = {"Q": r'[^"]*', "d": r"[-+]?\d+"}
_FIELD = re.compile(r"\{(\w+)(?::(\w+))?\}")


@dataclass
class StepDef:
    kind: str          # given | when | then | step
    pattern: str
    func: str
    file: str
    line: int
    doc: str

    @property
    def regex(self) -> re.Pattern:
        parts, pos = [], 0
        for m in _FIELD.finditer(self.pattern):
            parts.append(re.escape(self.pattern[pos:m.start()]))
            parts.append(f"(?:{_TYPES.get(m.group(2), '.+?')})")
            pos = m.end()
        parts.append(re.escape(self.pattern[pos:]))
        return re.compile("".join(parts))

    def matches(self, kind: str, text: str) -> bool:
        return self.kind in (kind, "step") and self.regex.fullmatch(text) is not None


def load_steps(steps_dir: Path = STEPS_DIR) -> list[StepDef]:
    steps = []
    for f in sorted(steps_dir.glob("*.py")):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            for dec in node.decorator_list:
                if (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name)
                        and dec.func.id in ("given", "when", "then", "step") and dec.args
                        and isinstance(dec.args[0], ast.Constant)):
                    doc = (ast.get_docstring(node) or "").strip().splitlines()
                    steps.append(StepDef(dec.func.id, dec.args[0].value, node.name,
                                         f.relative_to(ROOT).as_posix(), node.lineno, doc[0] if doc else ""))
    return steps


def split_step(line: str, previous_kind: str | None) -> tuple[str, str, str] | None:
    """'E que "Alice" ...' -> ('E', 'given', 'que "Alice" ...') herdando o tipo do passo anterior."""
    word, _, text = line.strip().partition(" ")
    if word not in KEYWORDS:
        return None
    kind = KEYWORDS[word] or previous_kind or "given"
    return word, kind, text.strip()


def find(steps: list[StepDef], kind: str, text: str) -> StepDef | None:
    return next((s for s in steps if s.matches(kind, text)), None)


def suggest_pattern(text: str) -> str:
    """Generaliza um passo novo: textos entre aspas -> {x:Q}, números -> {n:d}."""
    counter = iter(range(1, 100))
    out = re.sub(r'"[^"]*"', lambda _: '"{v%d:Q}"' % next(counter), text)
    return re.sub(r"(?<![\w{])\d+(?![\w}])", lambda _: "{n%d:d}" % next(counter), out)


def iter_gherkin_steps(text: str):
    """Percorre um texto Gherkin (pt) e devolve (linha, palavra, tipo, texto) de cada passo.
    Esquemas de cenário são expandidos com a PRIMEIRA linha de Exemplos (suficiente para casamento)."""
    lines = text.splitlines()
    i, prev, pending, headers = 0, None, [], None
    out = []

    def flush(row=None):
        for ln, word, kind, step_text in pending:
            if row:
                step_text = re.sub(r"<([^>]+)>", lambda m: row.get(m.group(1), m.group(0)), step_text)
            out.append((ln, word, kind, step_text))

    in_outline = False
    while i < len(lines):
        s = lines[i].strip()
        if s.startswith(("Cenário:", "Cenario:", "Contexto:", "Esquema do Cenário:", "Funcionalidade:")):
            if pending and not in_outline:
                flush()
            elif pending and in_outline and headers is None:
                flush()
            pending, headers, prev = [], None, None
            in_outline = s.startswith("Esquema")
        elif s.startswith("Exemplos:"):
            headers = "next"
        elif s.startswith("|") and headers == "next":
            headers = [c.strip() for c in s.strip("|").split("|")]
        elif s.startswith("|") and isinstance(headers, list):
            flush(dict(zip(headers, [c.strip() for c in s.strip("|").split("|")])))
            pending, headers = [], "done"
        else:
            parsed = split_step(s, prev)
            if parsed:
                prev = parsed[1]
                if in_outline:
                    pending.append((i + 1, *parsed))
                else:
                    out.append((i + 1, *parsed))
        i += 1
    if pending:
        flush()
    return out
