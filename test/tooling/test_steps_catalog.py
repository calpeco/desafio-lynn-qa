"""Todo passo das features tem definição; o catálogo está atualizado; o casamento segue o parse."""
import subprocess
import sys
from pathlib import Path

import pytest

from qa_support.steps_index import iter_gherkin_steps, load_steps, suggest_pattern

from qa_support.paths import FEATURES, SCRIPTS
STEPS = load_steps()


@pytest.mark.parametrize("feature", sorted(FEATURES.glob("*/*.feature")), ids=lambda p: p.name)
def test_todo_passo_tem_definicao(feature):
    orphans = []
    for line, word, kind, text in iter_gherkin_steps(feature.read_text(encoding="utf-8")):
        if not any(s.matches(kind, text) for s in STEPS):
            orphans.append(f"L{line}: {word} {text}")
    assert not orphans, "passos sem definição:\n" + "\n".join(orphans)


def test_nenhum_padrao_duplicado():
    seen = [(s.kind, s.pattern) for s in STEPS]
    assert len(seen) == len(set(seen))


def test_catalogo_atualizado():
    rc = subprocess.call([sys.executable, str(SCRIPTS / "step_catalog.py"), "--check"])
    assert rc == 0, "rode: python scripts/step_catalog.py"


def test_tipo_q_nao_atravessa_aspas():
    send = next(s for s in STEPS if s.pattern == '"{persona:Q}" envia a mensagem "{content:Q}"')
    assert send.matches("when", '"Alice" envia a mensagem "oi"')
    assert not send.matches("when", '"Alice" envia a mensagem "oi" na conversa de "Bob"')


def test_sugestao_de_padrao_generaliza_aspas_e_numeros():
    assert suggest_pattern('"Bob" avalia a 2ª resposta com "positivo" em 30 s') == \
        '"{v1:Q}" avalia a 2ª resposta com "{v2:Q}" em {n3:d} s'


def test_nenhum_passo_sem_uso():
    """Passo definido e não usado é código morto e polui o catálogo que o agente consulta."""
    used = set()
    for feature in FEATURES.glob("*/*.feature"):
        for _, _, kind, text in iter_gherkin_steps(feature.read_text(encoding="utf-8")):
            hit = next((s for s in STEPS if s.matches(kind, text)), None)
            if hit:
                used.add((hit.file, hit.func))
    unused = [f"{s.file}:{s.line} {s.func}" for s in STEPS if (s.file, s.func) not in used]
    assert not unused, "passos sem uso:\n" + "\n".join(unused)
