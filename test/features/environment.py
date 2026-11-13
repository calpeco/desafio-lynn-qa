"""Hooks do behave: sobe a API mock (ou usa LYNN_BASE_URL), isola cada cenário e gerencia o
navegador (Playwright) apenas quando há cenários @ui.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

TEST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TEST))          # qa_support
sys.path.insert(0, str(TEST / "features"))  # pages

from qa_support.paths import ROOT, bootstrap  # noqa: E402

bootstrap()  # lynn_mock (app/)

import parse  # noqa: E402  (dependência do behave)
from behave import register_type  # noqa: E402

from qa_support.environment_control import TestControl  # noqa: E402
from qa_support.reporting.naming import slug  # noqa: E402


@parse.with_pattern(r'[^"]*')
def _quoted(text: str) -> str:
    return text


# {x:Q} = conteúdo entre aspas, sem aspas internas: impede que um placeholder "engula" o resto
# do passo e torna os padrões não ambíguos.
register_type(Q=_quoted)


def before_all(context):
    context.evidence_dir = Path(os.getenv("LYNN_EVIDENCE_DIR", ROOT / ".artifacts"))
    context.evidence_dir.mkdir(parents=True, exist_ok=True)
    context.exchange_log = context.evidence_dir / "http_exchanges.jsonl"
    context.exchange_log.write_text("", encoding="utf-8")
    base_url = os.getenv("LYNN_BASE_URL")
    context.server = None
    if not base_url:
        from qa_support.embedded_server import EmbeddedServer

        context.server = EmbeddedServer().start()
        base_url = context.server.url
    context.base_url = base_url.rstrip("/")
    context.control = TestControl(context.base_url)
    # ATENÇÃO: o behave descarta, ao fim de cada cenário, atributos CRIADOS durante o cenário.
    # O navegador precisa sobreviver entre cenários, então mora num objeto criado aqui (nível
    # before_all) e só seus campos são alterados depois. Achado da revisão independente.
    context.ui = SimpleNamespace(playwright=None, browser=None)


def _ensure_browser(context):
    if context.ui.browser is None:
        from playwright.sync_api import sync_playwright

        context.ui.playwright = sync_playwright().start()
        context.ui.browser = context.ui.playwright.chromium.launch(
            headless=os.getenv("HEADED", "0") != "1", slow_mo=int(os.getenv("SLOW_MO", "0")))


def _failed(scenario) -> bool:
    # behave 1.2.6 usa "failed"; 1.2.7+/1.3 distinguem "error" (exceção que não é AssertionError)
    return getattr(scenario.status, "name", str(scenario.status)) in ("failed", "error")


def before_scenario(context, scenario):
    context.control.reset()
    context.control.llm("ok")
    context.clients, context.convs = {}, {}
    context.responses, context.sends, context.answers = [], [], []
    context.response, context.last_conv, context.background = None, None, {}
    if "ui" in scenario.effective_tags:
        _ensure_browser(context)
        context.browser_context = context.ui.browser.new_context(base_url=context.base_url, locale="pt-BR")
        context.browser_context.set_default_timeout(int(os.getenv("UI_TIMEOUT_MS", "5000")))
        context.page = context.browser_context.new_page()
        context.ui_requests = []
        context.page.on("request", lambda req: context.ui_requests.append((req.method, req.url)))


def after_scenario(context, scenario):
    if getattr(context, "page", None) is not None:
        # Evidência visual de TODO cenário de UI; o prefixo indica o resultado.
        shots = context.evidence_dir / "screenshots"
        shots.mkdir(parents=True, exist_ok=True)
        status = "FALHOU" if _failed(scenario) else "ok"
        name = slug(scenario.name)  # mesmo nome que o relatório usa para anexar o screenshot
        context.page.screenshot(path=str(shots / f"{status}__{name}.png"), full_page=True)
        context.browser_context.close()
        context.page = None
    for c in context.clients.values():
        c.close()
    context.control.llm("ok")


def after_all(context):
    if context.ui.browser:
        context.ui.browser.close()
        context.ui.playwright.stop()
    context.control.close()
    if context.server:
        context.server.stop()
