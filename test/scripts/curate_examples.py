"""Extrai de http_exchanges.jsonl um conjunto legível de exemplos de requisição/resposta."""
import json
from pathlib import Path

import sys

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "test/evidence/latest/http_exchanges.jsonl")
DST = Path(sys.argv[2] if len(sys.argv) > 2 else "test/evidence/EXEMPLOS_REQUISICOES.md")
PICK = [
    ("Fluxo feliz completo", "Criar, conversar, consultar o histórico e encerrar", None),
    ("Entrada inválida (4001 caracteres)", "4001 caracteres é rejeitado", "POST"),
    ("Mensagem em conversa encerrada", "Mensagem em conversa encerrada é recusada", 409),
    ("Acesso à conversa de outra pessoa", "Outra pessoa não lê conversa alheia", 404),
    ("LLM indisponível", "Usuário é informado quando não há resposta (indisponível)", 503),
    ("Reenvio com a mesma Idempotency-Key (replay)", "Reenvio após perda da resposta", None),
    ("Prompt injection bloqueado pelo guardrail", "Prompt injection não vaza o prompt de sistema (direto)", 201),
]
entries = [json.loads(l) for l in SRC.read_text(encoding="utf-8").splitlines() if l.strip()]
out = ["# Exemplos de requisições e respostas (extraídos da execução real)", "",
       "Gerado por `test/scripts/curate_examples.py` a partir de `test/evidence/latest/http_exchanges.jsonl` "
       "(log de todas as chamadas da camada de API; token mascarado).", ""]
for title, test, flt in PICK:
    sel = [e for e in entries if e.get("scenario", "").startswith(test)]
    if isinstance(flt, int):
        sel = [e for e in sel if e["response"]["status"] == flt][:1]
    elif flt == "POST":
        sel = [e for e in sel if e["request"]["method"] == "POST" and "/messages" in e["request"]["path"]][:1]
    else:
        sel = sel[:6]
    out += [f"## {title}", f"Cenário: *{test}*", ""]
    for e in sel:
        out += ["```http", f"{e['request']['method']} {e['request']['path']}"]
        out += [f"{k}: {v}" for k, v in e["request"]["headers"].items() if k != "Content-Type"]
        if e["request"]["body"]:
            try:
                body = json.dumps(json.loads(e["request"]["body"]), ensure_ascii=False)
            except (ValueError, TypeError):
                body = str(e["request"]["body"])
            out += ["", body]
        out += ["", f"→ {e['response']['status']}  ({e['response']['elapsed_ms']} ms)  {json.dumps(e['response']['headers'], ensure_ascii=False)}",
                json.dumps(e["response"]["body"], ensure_ascii=False, indent=2), "```", ""]
DST.write_text("\n".join(out), encoding="utf-8")
print(f"escrito {DST}")
