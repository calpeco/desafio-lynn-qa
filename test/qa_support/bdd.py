"""Helpers compartilhados pelos step definitions (behave). Mantém os steps curtos e legíveis."""
from __future__ import annotations

from .http_client import PERSONAS, ConversationsClient

DEFAULT_CONV = "principal"


def client(context, persona: str) -> ConversationsClient:
    if persona not in PERSONAS:
        raise AssertionError(f"Persona desconhecida: {persona!r}. Use uma de {list(PERSONAS)}")
    if persona not in context.clients:
        c = ConversationsClient(context.base_url, PERSONAS[persona], context.exchange_log, label=persona)
        c.scenario = context.scenario.name
        context.clients[persona] = c
    return context.clients[persona]


def remember(context, resp):
    context.response = resp
    context.responses.append(resp)
    return resp


def create_conversation(context, owner: str, name: str = DEFAULT_CONV) -> str:
    r = client(context, owner).create_conversation()
    assert r.status_code == 201, f"pré-condição falhou: {r.status_code} {r.text}"
    context.convs[(owner, name)] = r.json()["id"]
    context.last_conv = (owner, name)
    return r.json()["id"]


def conv_id(context, owner: str, name: str = DEFAULT_CONV) -> str:
    try:
        return context.convs[(owner, name)]
    except KeyError:
        raise AssertionError(f"'{owner}' não tem conversa '{name}' neste cenário") from None


def send(context, persona: str, content, *, owner: str | None = None, name: str = DEFAULT_CONV,
         key: str | None = None, headers: dict | None = None, json_body=None):
    owner = owner or persona
    cid = conv_id(context, owner, name)
    context.last_conv = (owner, name)
    r = client(context, persona).send_message(cid, content, idempotency_key=key, headers=headers, json_body=json_body)
    context.sends.append(r)
    return remember(context, r)


def messages(context, owner: str | None = None, name: str | None = None) -> list[dict]:
    owner, name = (owner, name or DEFAULT_CONV) if owner else context.last_conv
    r = client(context, owner).get_conversation(conv_id(context, owner, name))
    assert r.status_code == 200, r.text
    return r.json()["messages"]


def terms(raw: str) -> list[str]:
    """'a;b;c' -> ['a','b','c']; '-' ou vazio -> []"""
    return [t.strip() for t in raw.split(";") if t.strip() and t.strip() != "-"]
