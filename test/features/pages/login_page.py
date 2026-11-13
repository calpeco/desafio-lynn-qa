"""Tela de entrada: escolhe a pessoa usuária (tokens fictícios)."""
from .base_page import BasePage
from .chat_page import ChatPage


class LoginPage(BasePage):
    path = "/"

    def login_as(self, display_name: str) -> ChatPage:
        self.by_testid("user-select").select_option(label=display_name)
        self.by_testid("login-button").click()
        chat = ChatPage(self.page)
        chat.panel.wait_for(state="visible")
        return chat
