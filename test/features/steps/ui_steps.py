"""Step definitions de UI (Playwright). Só orquestram Page Objects; nenhum seletor aqui."""
from behave import given, step, then
from playwright.sync_api import expect

from pages.login_page import LoginPage

@given('que "{persona:Q}" entrou no chat pela interface')
def logged_in(context, persona):
    context.dialogs = []
    context.page.on("dialog", lambda d: (context.dialogs.append(d.message), d.dismiss()))
    context.chat = LoginPage(context.page).open().login_as(persona)


@given("que a próxima resposta de envio de mensagem será perdida na rede")
def lose_next_response(context):
    """Simula a Parte C: a requisição CHEGA ao servidor (route.fetch), mas a resposta não
    volta ao navegador (abort). O cliente não sabe se a mensagem foi salva."""
    state = {"done": False}

    def handler(route):
        if route.request.method == "POST" and not state["done"]:
            state["done"] = True
            route.fetch()                      # servidor processa de verdade
            route.abort("connectionreset")     # ...e a resposta "se perde"
        else:
            route.continue_()

    context.page.route("**/api/v1/conversations/*/messages", handler)


@step('inicia na interface uma nova conversa com o "{agent:Q}"')
def start_conversation(context, agent):
    context.chat.start_conversation(agent)


@step('envia na interface a mensagem "{content:Q}"')
def send_ui(context, content):
    context.chat.send(content)


@step('digita na interface "{content:Q}" e clica duas vezes em Enviar')
def double_click_ui(context, content):
    context.chat.type_and_double_click_send(content)


@step('clica em "Tentar novamente" na interface')
def retry_ui(context):
    context.chat.retry()


@step("encerra a conversa na interface")
def close_ui(context):
    context.chat.close_conversation()


@then("a interface mostra {users:d} mensagem(ns) do usuário e {assistants:d} do agente")
def ui_counts(context, users, assistants):
    # a página já esperou a rede ficar ociosa; expect() ainda tolera a renderização final
    detail = context.chat.messages()
    expect(context.chat.messages_with_role("user"), f"mensagens do usuário: {detail}").to_have_count(users)
    expect(context.chat.messages_with_role("assistant"), f"respostas: {detail}").to_have_count(assistants)


@then('a última mensagem na interface é do agente e contém "{text:Q}"')
def last_is_assistant(context, text):
    last = context.chat.messages()[-1]
    assert last.role == "assistant" and text in last.text, last


@then("o campo de mensagem está vazio")
def input_empty(context):
    expect(context.chat.message_input).to_have_value("")


@then('a interface exibe o erro "{text:Q}"')
def ui_error(context, text):
    expect(context.chat.error_banner).to_be_visible()
    assert text.lower() in context.chat.error_text().lower(), context.chat.error_text()


@then('a interface oferece "Tentar novamente"')
def retry_visible(context):
    expect(context.chat.retry_button).to_be_visible()


@then("a interface não exibe erro")
def no_error(context):
    expect(context.chat.error_banner).to_be_hidden()


@then("a interface fez {n:d} requisição(ões) de envio de mensagem")
def ui_request_count(context, n):
    sends = [u for m, u in context.ui_requests if m == "POST" and u.endswith("/messages")]
    assert len(sends) == n, sends


@then('a interface informa "{text:Q}"')
def ui_status(context, text):
    expect(context.chat.status).to_have_text(text)


@then("o campo de mensagem e o botão Enviar estão desabilitados")
def composer_disabled(context):
    expect(context.chat.message_input).to_be_disabled()
    expect(context.chat.send_button).to_be_disabled()


@then('a primeira mensagem do usuário aparece como o texto literal "{text:Q}"')
def literal_text(context, text):
    first_user = next(m for m in context.chat.messages() if m.role == "user")
    assert first_user.text == text, first_user


@then("nenhum diálogo JavaScript foi aberto")
def no_dialogs(context):
    assert context.dialogs == [], context.dialogs
