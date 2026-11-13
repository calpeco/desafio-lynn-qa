"""Avaliação (feedback) de respostas do agente: regras puras."""
from __future__ import annotations

from .validation import ValidationError

RATINGS = ("positive", "negative")
MAX_COMMENT = 500


def validate_feedback(body: dict) -> tuple[tuple[str, str | None] | None, ValidationError | None]:
    rating = body.get("rating")
    if rating not in RATINGS:
        return None, ValidationError("VALIDATION_ERROR", "rating deve ser 'positive' ou 'negative'.")
    comment = body.get("comment")
    if comment is not None and not isinstance(comment, str):
        return None, ValidationError("VALIDATION_ERROR", "comment deve ser texto.")
    comment = (comment or "").strip() or None
    if comment and len(comment) > MAX_COMMENT:
        return None, ValidationError("VALIDATION_ERROR", f"comment deve ter no máximo {MAX_COMMENT} caracteres.")
    return (rating, comment), None


def can_receive_feedback(message: dict) -> bool:
    """Só respostas concluídas do agente podem ser avaliadas."""
    return message["role"] == "assistant" and message["status"] == "completed"
