"""Steps de UI da avaliação de respostas (FDBK). Só orquestram o ChatPage; nenhum seletor aqui."""
from behave import step, then
from playwright.sync_api import expect

ICONS = {"👍": "positive", "👎": "negative"}


def _rating(icon: str) -> str:
    assert icon in ICONS, f"ícone desconhecido {icon!r}; use 👍 ou 👎"
    return ICONS[icon]


@step("avalia na interface a última resposta do agente com {icon}")
def give_feedback_ui(context, icon):
    context.chat.give_feedback(_rating(icon))


@then("a interface agradece a avaliação")
def thanks_visible(context):
    expect(context.chat.feedback_thanks).to_have_count(1)
    expect(context.chat.feedback_thanks).to_have_text("Obrigado pelo feedback!")


@then("o botão {icon} da última resposta fica destacado")
def button_pressed(context, icon):
    chosen = _rating(icon)
    other = next(r for r in ICONS.values() if r != chosen)
    expect(context.chat.feedback_button(chosen)).to_have_attribute("aria-pressed", "true")
    expect(context.chat.feedback_button(other)).to_have_attribute("aria-pressed", "false")


@then("cada resposta do agente mostra os botões 👍 e 👎 e as mensagens do usuário não")
def buttons_only_on_answers(context):
    answers = context.chat.messages_with_role("assistant")
    n = answers.count()
    assert n > 0, "nenhuma resposta do agente na tela"
    for i in range(n):
        for rating in ICONS.values():
            btn = context.chat.feedback_button(rating, answers.nth(i))
            expect(btn).to_be_visible()
            expect(btn).to_have_attribute("aria-pressed", "false")
    expect(context.chat.feedback_buttons_in("user")).to_have_count(0)


@then("o texto das respostas do agente não inclui os botões de avaliação")
def text_without_buttons(context):
    texts = context.chat.message_texts("assistant")
    assert texts and all("👍" not in t and "👎" not in t for t in texts), texts


@then('a interface fez {n:d} requisição(ões) de avaliação')
def feedback_request_count(context, n):
    posts = [u for m, u in context.ui_requests if m == "POST" and u.endswith("/feedback")]
    assert len(posts) == n, posts

