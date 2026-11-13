"""Conversas e mensagens em memória. Regras de estado e ordem do histórico."""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


class ConversationStore:
    """Lock global curto para leitura/escrita + lock por conversa durante a geração (ordem)."""

    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.reset()

    def reset(self) -> None:
        with self.lock:
            self._conversations: dict[str, dict] = {}
            self._conv_locks: dict[str, threading.Lock] = {}

    # ------------------------------------------------------------- consultas
    def create(self, owner_id: str, agent_id: str) -> dict:
        conv = {"id": new_id("conv"), "agent_id": agent_id, "owner_id": owner_id, "status": "open",
                "created_at": now_iso(), "closed_at": None, "messages": []}
        with self.lock:
            self._conversations[conv["id"]] = conv
            self._conv_locks[conv["id"]] = threading.Lock()
        return conv

    def get_owned(self, conv_id: str, user_id: str, *, ignore_owner: bool = False) -> dict | None:
        """Conversa inexistente e conversa alheia são indistinguíveis (premissa P-6)."""
        with self.lock:
            conv = self._conversations.get(conv_id)
            if conv is None or (conv["owner_id"] != user_id and not ignore_owner):
                return None
            return conv

    def snapshot(self, conv: dict) -> dict:
        with self.lock:
            return {**conv, "messages": [dict(m) for m in conv["messages"]]}

    def conversation_lock(self, conv_id: str) -> threading.Lock:
        return self._conv_locks[conv_id]

    def all_message_contents(self) -> list[str]:
        with self.lock:
            return [m["content"] for c in self._conversations.values() for m in c["messages"]]

    # ------------------------------------------------------------- comandos
    def close(self, conv: dict) -> bool:
        """Idempotente (P-10). Retorna True se mudou o estado."""
        with self.lock:
            if conv["status"] == "closed":
                return False
            conv["status"], conv["closed_at"] = "closed", now_iso()
            return True

    def append_user_message(self, conv: dict, content: str) -> dict:
        with self.lock:
            msg = {"id": new_id("msg"), "seq": len(conv["messages"]) + 1, "role": "user", "content": content,
                   "status": "completed", "created_at": now_iso(), "reply_to": None, "metadata": None,
                   "feedback": None}
            conv["messages"].append(msg)
            return msg

    def append_assistant_message(self, conv: dict, reply_to: dict, content: str, metadata: dict) -> dict:
        with self.lock:
            msg = {"id": new_id("msg"), "seq": len(conv["messages"]) + 1, "role": "assistant",
                   "content": content, "status": "completed", "created_at": now_iso(),
                   "reply_to": reply_to["id"], "metadata": metadata, "feedback": None}
            conv["messages"].append(msg)
            return msg

    def find_message(self, conv: dict, message_id: str) -> dict | None:
        with self.lock:
            return next((m for m in conv["messages"] if m["id"] == message_id), None)

    def set_feedback(self, message: dict, rating: str, comment: str | None) -> dict:
        """Uma avaliação por mensagem: a nova substitui a anterior."""
        with self.lock:
            message["feedback"] = {"rating": rating, "comment": comment, "updated_at": now_iso()}
            return dict(message["feedback"])

    def reusable_failed_message(self, conv: dict, message_id: str | None) -> dict | None:
        """Mensagem 'failed' só é reaproveitada se ainda for a última do histórico (P-8):
        a resposta nunca é inserida 'no passado'."""
        with self.lock:
            if message_id and conv["messages"] and conv["messages"][-1]["id"] == message_id:
                return conv["messages"][-1]
            return None

    @staticmethod
    def llm_context(conv: dict, exclude: dict) -> list[str]:
        """Contexto enviado ao LLM: só mensagens concluídas desta conversa."""
        return [m["content"] for m in conv["messages"] if m is not exclude and m["status"] == "completed"]
