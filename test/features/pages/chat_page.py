"""Tela do chat. Os steps falam em intenção ("enviar mensagem"); o como fica aqui."""
from dataclasses import dataclass

from .base_page import BasePage


@dataclass(frozen=True)
class UiMessage:
    role: str
    text: str
    status: str


class ChatPage(BasePage):
    @property
    def panel(self):
        return self.by_testid("chat-panel")

    @property
    def message_input(self):
        return self.by_testid("message-input")

    @property
    def send_button(self):
        return self.by_testid("send-button")

    @property
    def retry_button(self):
        return self.by_testid("retry-button")

    @property
    def status(self):
        return self.by_testid("conversation-status")

    def messages_with_role(self, role: str):
        return self.by_testid("message-list").locator(f'[data-testid="message"][data-role="{role}"]')

    @property
    def last_assistant_message(self):
        return self.messages_with_role("assistant").last

    def feedback_button(self, rating: str, message=None):
        """rating: "positive" (👍) ou "negative" (👎). Por padrão, na última resposta do agente."""
        return (message or self.last_assistant_message).get_by_test_id(f"feedback-{rating}")

    def feedback_buttons_in(self, role: str):
        return self.messages_with_role(role).locator(
            '[data-testid="feedback-positive"], [data-testid="feedback-negative"]')

    @property
    def feedback_thanks(self):
        return self.by_testid("feedback-thanks")

    @property
    def error_banner(self):
        return self.by_testid("error-banner")

    # ---------------------------------------------------------------- ações
    def start_conversation(self, agent_label: str) -> None:
        self.by_testid("agent-select").select_option(label=agent_label)
        self.by_testid("new-conversation-button").click()
        self.status.get_by_text("Conversa aberta.").wait_for()

    def send(self, text: str) -> None:
        self.message_input.fill(text)
        self.send_button.click()
        self.wait_until_settled()

    def type_and_double_click_send(self, text: str) -> None:
        """Dois cliques reais em sequência. Não usa dblclick(): o indicador "digitando" aparece
        após o 1º clique e desloca o botão, então o 2º clique do dblclick cai fora dele e o teste
        passaria por acidente de layout. force=True no 2º clique = a pessoa clica de novo SEM
        esperar o botão reabilitar (se estiver desabilitado, o navegador ignora — que é a proteção)."""
        self.message_input.fill(text)
        self.send_button.click()
        self.send_button.click(force=True, no_wait_after=True)
        self.wait_until_settled()

    def retry(self) -> None:
        self.retry_button.click()
        self.wait_until_settled()

    def give_feedback(self, rating: str) -> None:
        """Avalia a última resposta do agente e espera o POST + a releitura do histórico."""
        self.feedback_button(rating).click()
        self.wait_until_settled()

    def close_conversation(self) -> None:
        self.by_testid("close-conversation-button").click()
        self.wait_until_settled()

    # ---------------------------------------------------------------- leitura
    def messages(self) -> list[UiMessage]:
        items = self.by_testid("message-list").get_by_test_id("message")
        return [UiMessage(i.get_attribute("data-role"), i.inner_text(), i.get_attribute("data-status"))
                for i in items.all()]

    def message_texts(self, role: str) -> list[str]:
        """Só o conteúdo das bolhas (data-testid message-text), sem os botões de avaliação."""
        return self.messages_with_role(role).get_by_test_id("message-text").all_inner_texts()

    def error_text(self) -> str:
        return self.by_testid("error-text").inner_text() if self.error_banner.is_visible() else ""

