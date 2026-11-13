"""Store de idempotência para POST /messages (premissa P-3).

Escopo (usuário, conversa, chave); fingerprint do corpo; estados in_progress/completed/failed;
TTL. Relógio injetável para teste unitário determinístico.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class Decision(Enum):
    PROCEED = "proceed"              # primeira vez (ou expirada): processar
    RETRY_FAILED = "retry_failed"    # tentativa anterior falhou: reprocessar sem duplicar
    REPLAY = "replay"                # já concluída: devolver a resposta armazenada
    IN_PROGRESS = "in_progress"      # outra requisição com a mesma chave está em curso
    KEY_REUSED = "key_reused"        # mesma chave, corpo diferente


@dataclass
class Record:
    fingerprint: str
    created: float
    state: str = "in_progress"
    user_message_id: str | None = None
    response: tuple | None = None


@dataclass
class BeginResult:
    decision: Decision
    record: Record | None = None


@dataclass
class IdempotencyStore:
    ttl_s: float = 24 * 3600
    clock: Callable[[], float] = time.time
    _records: dict = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def begin(self, scope: tuple, fingerprint: str) -> BeginResult:
        """Operação atômica de 'check-and-set': é aqui que mora a proteção contra duplo clique."""
        with self._lock:
            rec = self._records.get(scope)
            if rec and self.clock() - rec.created > self.ttl_s:
                rec = None
            if rec is None:
                self._records[scope] = Record(fingerprint, self.clock())
                return BeginResult(Decision.PROCEED, self._records[scope])
            if rec.fingerprint != fingerprint:
                return BeginResult(Decision.KEY_REUSED, rec)
            if rec.state == "in_progress":
                return BeginResult(Decision.IN_PROGRESS, rec)
            if rec.state == "completed":
                return BeginResult(Decision.REPLAY, rec)
            rec.state = "in_progress"  # failed -> reprocessa, mantendo user_message_id
            return BeginResult(Decision.RETRY_FAILED, rec)

    def complete(self, scope: tuple, response: tuple) -> None:
        with self._lock:
            if scope in self._records:
                self._records[scope].state, self._records[scope].response = "completed", response

    def fail(self, scope: tuple, user_message_id: str | None = None) -> None:
        """Marca falha. Não apaga um user_message_id já registrado (reenvio não pode duplicar)."""
        with self._lock:
            rec = self._records.get(scope)
            if rec:
                rec.state = "failed"
                if user_message_id is not None:
                    rec.user_message_id = user_message_id

    def release(self, scope: tuple) -> None:
        with self._lock:
            self._records.pop(scope, None)

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
