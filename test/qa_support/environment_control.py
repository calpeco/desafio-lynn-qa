"""Controle do ambiente de teste (/__test__): reset, comportamento do LLM simulado, stats e logs."""
from __future__ import annotations

import httpx


class TestControl:
    def __init__(self, base_url: str):
        self._http = httpx.Client(base_url=base_url, timeout=5)

    def _post(self, path: str, body: dict | None = None) -> dict:
        r = self._http.post(path, json=body or {})
        r.raise_for_status()
        return r.json()

    def reset(self) -> dict:
        return self._post("/__test__/reset")

    def llm(self, mode: str = "ok", delay_ms: int = 0, timeout_ms: int = 10_000) -> dict:
        return self._post("/__test__/llm", {"mode": mode, "delay_ms": delay_ms, "timeout_ms": timeout_ms})

    def config(self, **values) -> dict:
        return self._post("/__test__/config", values)

    def stats(self) -> dict:
        return self._http.get("/__test__/stats").json()

    def logs(self) -> list[dict]:
        return self._http.get("/__test__/logs").json()

    def close(self) -> None:
        self._http.close()
