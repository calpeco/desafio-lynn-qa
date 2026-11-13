"""Sobe a API mock em thread (porta aleatória, multithread) para a suíte rodar sem setup externo."""
from __future__ import annotations

import logging
import threading

from werkzeug.serving import make_server


class EmbeddedServer:
    def __init__(self):
        from lynn_mock.api.app import create_app  # importa aqui: LYNN_FAULTS é lido na criação

        logging.getLogger("werkzeug").setLevel(logging.WARNING)
        self._server = make_server("127.0.0.1", 0, create_app(test_control=True), threaded=True)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_port}"

    def start(self) -> "EmbeddedServer":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._server.shutdown()
