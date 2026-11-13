"""Nomes derivados compartilhados entre o runner (screenshots) e os relatórios."""
import re


def slug(text: str, limit: int = 80) -> str:
    return re.sub(r"[^\w-]+", "_", text, flags=re.ASCII).strip("_")[:limit]
