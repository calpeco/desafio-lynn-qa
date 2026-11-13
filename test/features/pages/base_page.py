"""Page Object base: navegação, seletores estáveis (data-testid) e espera por rede ociosa."""
import time

from playwright.sync_api import Locator, Page


class BasePage:
    path = "/"

    def __init__(self, page: Page):
        self.page = page
        # Rastreamento de requisições em voo, por página (sem ganchos no código da aplicação).
        if not hasattr(page, "_lynn_inflight"):
            page._lynn_inflight = set()
            page.on("request", lambda r: page._lynn_inflight.add(r))
            page.on("requestfinished", lambda r: page._lynn_inflight.discard(r))
            page.on("requestfailed", lambda r: page._lynn_inflight.discard(r))

    def open(self) -> "BasePage":
        self.page.goto(self.path)
        return self

    def by_testid(self, testid: str) -> Locator:
        return self.page.get_by_test_id(testid)

    def wait_until_settled(self, timeout_ms: int = 8000, quiet_ms: int = 200) -> None:
        """Espera até não haver requisições por `quiet_ms` seguidos. A janela de silêncio pega um
        segundo envio disparado logo depois do primeiro (cenário de duplo clique)."""
        deadline = time.monotonic() + timeout_ms / 1000
        quiet_since = None
        while time.monotonic() < deadline:
            self.page.wait_for_timeout(25)  # processa eventos do navegador
            if self.page._lynn_inflight:
                quiet_since = None
            elif quiet_since is None:
                quiet_since = time.monotonic()
            elif (time.monotonic() - quiet_since) * 1000 >= quiet_ms:
                return
        raise TimeoutError(f"requisições ainda em andamento após {timeout_ms} ms: "
                           f"{[r.url for r in self.page._lynn_inflight]}")
