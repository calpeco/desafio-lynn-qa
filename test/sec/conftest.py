"""Fixtures da suíte de segurança (test/sec).

Alvo: a instância embutida (padrão) ou LYNN_BASE_URL, se apontar para ambiente de teste da equipe.
Estado e modo do LLM são resetados ANTES de cada teste (fixture autouse) para independência.
Os resultados vão para LYNN_SEC_RESULTS ou test/reports/raw/sec-results.json (mesmo formato do
unit, com "layer": "sec" e as tags owasp + trace).
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import httpx
import pytest

from qa_support.embedded_server import EmbeddedServer
from qa_support.environment_control import TestControl
from qa_support.http_client import PERSONAS, ConversationsClient
from qa_support.paths import RAW

from sec_support import new_conversation, send_ok

_RESULTS: list[dict] = []


# ================================================================== relatório JSON
def _status(rep) -> str:
    if hasattr(rep, "wasxfail"):
        return "xfailed" if rep.skipped else "failed"   # XPASS(strict) já vem como failed
    return "passed" if rep.passed else ("skipped" if rep.skipped else "failed")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call" or (rep.when == "setup" and rep.outcome != "passed"):
        tags = sorted({t for name in ("owasp", "trace") for m in item.iter_markers(name) for t in m.args})
        _RESULTS.append({
            "id": item.nodeid, "file": item.location[0], "name": item.name,
            "status": _status(rep), "duration_s": round(rep.duration, 4), "tags": tags,
            "error": str(rep.longrepr)[:2000] if rep.failed else (getattr(rep, "wasxfail", None) or None),
        })


def pytest_sessionfinish(session, exitstatus):
    out = Path(os.getenv("LYNN_SEC_RESULTS", RAW / "sec-results.json"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"layer": "sec", "finished_at": time.time(), "tests": _RESULTS},
                              ensure_ascii=False, indent=1), encoding="utf-8")


# ================================================================== servidor e controle
@pytest.fixture(scope="session")
def base_url():
    external = os.getenv("LYNN_BASE_URL")
    if external:
        yield external.rstrip("/")
        return
    server = EmbeddedServer().start()
    yield server.url
    server.stop()


@pytest.fixture(scope="session")
def control(base_url):
    c = TestControl(base_url)
    yield c
    c.close()


@pytest.fixture(autouse=True)
def _reset(control):
    control.reset()   # limpa conversas, idempotência, logs e restaura o LLM (modo ok, timeout padrão)
    yield


# ================================================================== clientes por persona
@pytest.fixture
def client_factory(base_url):
    made: list[ConversationsClient] = []

    def make(persona: str | None = None, token: str | None = None, **kw) -> ConversationsClient:
        c = ConversationsClient(base_url, token if persona is None else PERSONAS[persona], label=persona or "", **kw)
        made.append(c)
        return c

    yield make
    for c in made:
        c.close()


@pytest.fixture
def alice(client_factory):
    return client_factory("Alice")


@pytest.fixture
def bob(client_factory):
    return client_factory("Bob")


@pytest.fixture
def visitante(client_factory):
    return client_factory("Visitante")


@pytest.fixture
def raw_http(base_url):
    """httpx cru: para headers/métodos/corpos que o cliente de domínio não monta."""
    with httpx.Client(base_url=base_url, timeout=20) as c:
        yield c


# ================================================================== dados prontos
@pytest.fixture
def alice_conv(alice):
    """Conversa da Alice com uma troca concluída (ids da mensagem do usuário e da resposta)."""
    conv = new_conversation(alice)
    body = send_ok(alice, conv["id"], "Mensagem privada da Alice")
    return {"id": conv["id"], "user_msg": body["user_message"]["id"], "assistant_msg": body["assistant_message"]["id"]}
