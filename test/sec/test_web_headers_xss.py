"""UI: headers de segurança do frontend (API8:2023) e XSS armazenado chegando à interface (R18).

XSS: o payload percorre o caminho completo (UI → API → LLM ecoa → histórico → render) num Chromium
headless real (Playwright), contra a instância local. Reaproveita os Page Objects de test/features/pages.
"""
from __future__ import annotations

import pytest

from features.pages.login_page import LoginPage
from payloads import XSS_PAYLOADS

pytestmark = pytest.mark.owasp("API8:2023")

UI_HEADERS = {
    "content-security-policy": lambda v: v and "script-src" in v and "'unsafe-inline'" not in v,
    "x-content-type-options": lambda v: (v or "").lower() == "nosniff",
    "anti-clickjacking": None,   # tratado à parte: X-Frame-Options OU CSP frame-ancestors
    "referrer-policy": lambda v: (v or "").lower() in ("no-referrer", "same-origin", "strict-origin",
                                                       "strict-origin-when-cross-origin"),
}


@pytest.mark.trace("R18")
@pytest.mark.xfail(strict=True, reason="SEC-005: página do chat sem headers de segurança (CSP, nosniff, frame, referrer)")
@pytest.mark.parametrize("header", list(UI_HEADERS))
def test_pagina_do_chat_envia_header_de_seguranca(header, raw_http):
    h = raw_http.get("/").headers
    if header == "anti-clickjacking":
        ok = h.get("x-frame-options", "").upper() in ("DENY", "SAMEORIGIN") or \
            "frame-ancestors" in h.get("content-security-policy", "")
    else:
        ok = UI_HEADERS[header](h.get(header))
    assert ok, f"{header} ausente ou fraco: {h.get(header)!r}"


@pytest.mark.trace("R18")
@pytest.mark.parametrize("path,ctype", [("/", "text/html"), ("/config.js", "application/javascript"),
                                        ("/static/chat.js", "text/javascript")])
def test_assets_da_ui_tem_content_type_correto(path, ctype, raw_http):
    r = raw_http.get(path)
    assert r.status_code == 200 and r.headers["Content-Type"].startswith(ctype), r.headers["Content-Type"]


# ------------------------------------------------------------------ XSS armazenado (Playwright)
@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def page(browser, base_url):
    ctx = browser.new_context(base_url=base_url)
    pg = ctx.new_page()
    pg.dialogs = []
    pg.on("dialog", lambda d: (pg.dialogs.append(d.message), d.dismiss()))
    # Bloqueia qualquer saída para fora da instância local (um payload não pode chamar a internet).
    pg.route("**/*", lambda route: route.continue_() if route.request.url.startswith(base_url) else route.abort())
    yield pg
    ctx.close()


@pytest.mark.owasp("API8:2023", "LLM05:2025")
@pytest.mark.trace("CONV-RN05", "R18")
@pytest.mark.parametrize("payload_id,payload", XSS_PAYLOADS, ids=[p[0] for p in XSS_PAYLOADS])
def test_xss_armazenado_na_mensagem_e_na_resposta_do_agente_nao_executa(payload_id, payload, page):
    chat = LoginPage(page).open().login_as("Alice")
    chat.start_conversation("Agente de suporte")
    chat.send(payload)
    chat.last_assistant_message.wait_for()

    assert page.evaluate("typeof window.__xss") == "undefined", f"payload {payload_id} executou"
    assert page.dialogs == []
    msgs = chat.messages()
    assert msgs[0].role == "user" and msgs[0].text == payload, "conteúdo do usuário não exibido literalmente"
    assert payload in msgs[1].text, "o agente ecoa o texto; deve aparecer literal, não renderizado"
    injected = page.locator('[data-testid="message-list"] img, [data-testid="message-list"] svg, '
                            '[data-testid="message-list"] script')
    assert injected.count() == 0, "elemento HTML do payload foi criado no DOM"


@pytest.mark.owasp("API8:2023", "LLM05:2025")
@pytest.mark.trace("R18")
def test_controle_positivo_o_detector_de_xss_funciona(page):
    """Prova que o teste acima não passa por acidente: o mesmo payload, se interpretado como HTML
    (innerHTML), executa e é detectado por window.__xss. Usa o img-onerror: <script> e <svg onload>
    inseridos via innerHTML não disparam no Chromium, então não serviriam de controle."""
    payload = dict(XSS_PAYLOADS)["img-onerror"]
    LoginPage(page).open()
    page.evaluate("p => { const d = document.createElement('div'); d.innerHTML = p; document.body.appendChild(d); }",
                  payload)
    page.wait_for_function("window.__xss === 1", timeout=3000)


@pytest.mark.owasp("API2:2023")
@pytest.mark.trace("CONV-RN01", "R16")
def test_token_nao_fica_em_armazenamento_persistente_do_navegador(page):
    """Token só em memória: um XSS futuro ou outro usuário da máquina não o encontra em storage/cookie."""
    chat = LoginPage(page).open().login_as("Alice")
    chat.start_conversation("Agente de suporte")
    chat.send("oi")
    storage = page.evaluate("JSON.stringify([Object.entries(localStorage), Object.entries(sessionStorage)])")
    assert "token-" not in storage
    assert all("token-" not in c["value"] for c in page.context.cookies())
