"""Helpers de domínio da suíte de segurança (sem fixtures): criar conversa, enviar, checar vazamento."""
from __future__ import annotations

import json

from qa_support.contracts import assert_matches
from qa_support.environment_control import TestControl
from qa_support.http_client import ConversationsClient

from payloads import CANARY_PREFIX, SYSTEM_PROMPT_FRAGMENTS


def new_conversation(client: ConversationsClient, agent_id: str = "agt_support") -> dict:
    r = client.create_conversation(agent_id)
    assert r.status_code == 201, r.text
    assert_matches("conversation", r.json())
    return r.json()


def send_ok(client: ConversationsClient, conv_id: str, content: str) -> dict:
    r = client.send_message(conv_id, content)
    assert r.status_code == 201, r.text
    assert_matches("send_message_response", r.json())
    return r.json()


def assert_no_system_prompt(text: str, where: str) -> None:
    assert CANARY_PREFIX not in text, f"canário do prompt de sistema vazou em {where}"
    for frag in SYSTEM_PROMPT_FRAGMENTS:
        assert frag not in text, f"trecho do prompt de sistema ({frag!r}) vazou em {where}"


def logs_text(control: TestControl) -> str:
    return json.dumps(control.logs(), ensure_ascii=False)
