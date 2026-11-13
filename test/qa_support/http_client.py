"""Cliente HTTP (httpx) da API de conversas, usado pelos step definitions.

Os steps descrevem intenção de negócio; detalhes de HTTP ficam aqui. Toda troca é gravada em
JSONL (token mascarado) como evidência de execução.
"""
from __future__ import annotations

import json
import os
import re
import threading
import uuid
from pathlib import Path

import httpx

_log_lock = threading.Lock()

# Evidência não pode virar vazamento: campos livres e padrões de dado pessoal são mascarados no log
# (achado do agent-qa-lynn ao automatizar a RN08 da spec de feedback).
SENSITIVE_FIELDS = {"comment"}
_PII = [re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"),          # CPF
        re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b")]                  # cartão


def redact(content):
    if not isinstance(content, str):
        return content
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            data = {k: ("***" if k in SENSITIVE_FIELDS and v else v) for k, v in data.items()}
            content = json.dumps(data, ensure_ascii=False)
    except ValueError:
        pass
    for pattern in _PII:
        content = pattern.sub("***", content)
    return content

# Tokens vêm do ambiente (secrets do GitHub em dev/hom); os padrões só valem para a aplicação mock.
PERSONAS = {
    "Alice": os.getenv("LYNN_TOKEN_ALICE") or "token-alice",
    "Bob": os.getenv("LYNN_TOKEN_BOB") or "token-bob",
    "Visitante": None,
}


class ConversationsClient:
    def __init__(self, base_url: str, token: str | None, exchange_log: Path | None = None,
                 label: str = "", timeout: float = 15, default_headers: dict | None = None):
        self.token = token
        self.default_headers = default_headers or {}
        self.label = label
        self.exchange_log = exchange_log
        self.scenario = ""
        # httpx.Client é thread-safe para requisições concorrentes (cenários de duplo clique).
        self._http = httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout)

    def close(self) -> None:
        self._http.close()

    # ---------------------------------------------------------------- baixo nível
    def request(self, method: str, path: str, *, json_body=None, raw_body: str | None = None,
                headers: dict | None = None) -> httpx.Response:
        h = {"X-Request-ID": f"qa-{uuid.uuid4()}"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        content = raw_body if raw_body is not None else (json.dumps(json_body) if json_body is not None else None)
        if content is not None:
            h["Content-Type"] = "application/json"
        h.update(self.default_headers)
        h.update(headers or {})
        h = {k: v for k, v in h.items() if v is not None}
        resp = self._http.request(method, path, content=content, headers=h)
        self._record(method, path, h, content, resp)
        return resp

    def _record(self, method, path, headers, content, resp) -> None:
        if not self.exchange_log:
            return
        try:
            body = resp.json()
        except ValueError:
            body = resp.text[:500]
        entry = {
            "scenario": self.scenario,
            "request": {"method": method, "path": path,
                        "headers": {k: ("Bearer ***" if k == "Authorization" else v) for k, v in headers.items()},
                        "body": _clip(redact(content))},
            "response": {"status": resp.status_code,
                         "headers": {k: v for k, v in resp.headers.items()
                                     if k.lower() in ("x-request-id", "retry-after", "idempotent-replayed")},
                         "elapsed_ms": int(resp.elapsed.total_seconds() * 1000),
                         "body": _truncate(_mask_response(body))},
        }
        with _log_lock, self.exchange_log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # ---------------------------------------------------------------- domínio
    def create_conversation(self, agent_id: str = "agt_support") -> httpx.Response:
        return self.request("POST", "/api/v1/conversations", json_body={"agent_id": agent_id})

    def send_message(self, conv_id: str, content, idempotency_key: str | None = None,
                     headers: dict | None = None, json_body=None) -> httpx.Response:
        h = dict(headers or {})
        if idempotency_key:
            h["Idempotency-Key"] = idempotency_key
        body = json_body if json_body is not None else {"content": content}
        return self.request("POST", f"/api/v1/conversations/{conv_id}/messages", json_body=body, headers=h)

    def get_conversation(self, conv_id: str, headers: dict | None = None) -> httpx.Response:
        return self.request("GET", f"/api/v1/conversations/{conv_id}", headers=headers)

    def give_feedback(self, conv_id: str, message_id: str, body: dict | None = None,
                      raw_body: str | None = None) -> httpx.Response:
        return self.request("POST", f"/api/v1/conversations/{conv_id}/messages/{message_id}/feedback",
                            json_body=body, raw_body=raw_body)

    def close_conversation(self, conv_id: str) -> httpx.Response:
        return self.request("POST", f"/api/v1/conversations/{conv_id}/close")


def _mask_response(body):
    if isinstance(body, dict):
        return {k: ("***" if k in SENSITIVE_FIELDS and v else _mask_response(v)) for k, v in body.items()}
    if isinstance(body, list):
        return [_mask_response(v) for v in body]
    if isinstance(body, str):
        for pattern in _PII:
            body = pattern.sub("***", body)
    return body


def _clip(content):
    return (content[:300] + "…") if isinstance(content, str) and len(content) > 300 else content


def _truncate(obj, limit: int = 400):
    if isinstance(obj, str):
        return obj if len(obj) <= limit else obj[:limit] + f"…(+{len(obj) - limit})"
    if isinstance(obj, dict):
        return {k: _truncate(v, limit) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_truncate(v, limit) for v in obj[:20]]
    return obj
