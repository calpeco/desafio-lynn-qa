"""Camada HTTP (Flask) da API mock "Conversa com agente" + frontend mínimo de chat.

Segue app/CONTRATO_API.md. As regras ficam em app/lynn_mock/domain (testadas na base da
pirâmide); aqui só há orquestração, HTTP e logs. Defeitos podem ser injetados via LYNN_FAULTS
para demonstrar que a suíte os detecta.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from pathlib import Path

from flask import Flask, Response, g, jsonify, request, send_from_directory

from ..domain.conversations import ConversationStore, now_iso
from ..domain.feedback import can_receive_feedback, validate_feedback
from ..domain.guardrail import apply_output_guardrail
from ..domain.http_rules import (error_body, llm_failure_response, parse_json_object,
                                 request_id, resolve_user)
from ..domain.idempotency import Decision, IdempotencyStore
from ..domain.validation import MAX_CONTENT, validate_agent, validate_content
from ..llm.fake_llm import SYSTEM_CANARY, FakeLLM, LLMUnavailable

TOKENS = {"token-alice": "u_alice", "token-bob": "u_bob"}  # credenciais FICTÍCIAS
CLOSED_MSG = "Esta conversa foi encerrada. Inicie uma nova conversa."
PUBLIC_PREFIXES = ("/__test__", "/static/")
PUBLIC_PATHS = ("/", "/config.js", "/favicon.ico")
STATIC_DIR = Path(__file__).resolve().parents[1] / "web" / "static"
_LLM_POOL = ThreadPoolExecutor(max_workers=32, thread_name_prefix="llm")


def _err(status: int, code: str, message: str, headers: dict | None = None):
    return jsonify(error_body(code, message, g.request_id)), status, (headers or {})


def create_app(faults: set[str] | None = None, test_control: bool | None = None) -> Flask:
    app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")
    app.json.sort_keys = False
    app.json.ensure_ascii = False
    faults = set(faults if faults is not None else filter(None, os.getenv("LYNN_FAULTS", "").split(",")))
    if test_control is None:
        test_control = os.getenv("LYNN_TEST_CONTROL", "1") == "1"
    store, llm = ConversationStore(), FakeLLM()
    default_ttl = int(os.getenv("LYNN_IDEMPOTENCY_TTL_S", str(24 * 3600)))
    idem = IdempotencyStore(ttl_s=default_ttl)
    log_buffer: deque[dict] = deque(maxlen=2000)
    logger = logging.getLogger("lynn.mock")

    def log(event: str, **fields) -> None:
        # Log estruturado. NUNCA registra o conteúdo da mensagem (PII): só tamanho e hash.
        rec = {"ts": now_iso(), "event": event, "request_id": g.get("request_id"), **fields}
        log_buffer.append(rec)
        logger.info(json.dumps(rec, ensure_ascii=False))

    # ================================================================== middleware
    @app.before_request
    def _before():
        g.request_id = request_id(request.headers.get("X-Request-ID"))
        g.t0 = time.monotonic()
        g.user = None
        if request.path in PUBLIC_PATHS or request.path.startswith(PUBLIC_PREFIXES):
            return None
        g.user = resolve_user(request.headers.get("Authorization"), TOKENS)
        if not g.user:
            log("auth.rejected", path=request.path)
            return _err(401, "UNAUTHENTICATED", "Autenticação necessária.")
        return None

    @app.after_request
    def _after(resp):
        resp.headers["X-Request-ID"] = g.get("request_id", "")
        if request.path.startswith("/api/"):
            log("http.access", method=request.method, path=request.path, status=resp.status_code,
                user_id=g.get("user"), duration_ms=int((time.monotonic() - g.get("t0", time.monotonic())) * 1000))
        return resp

    @app.errorhandler(404)
    def _nf(_e):
        return _err(404, "NOT_FOUND", "Recurso não encontrado.")

    @app.errorhandler(405)
    def _na(_e):
        return _err(405, "METHOD_NOT_ALLOWED", "Método não permitido.")

    @app.errorhandler(Exception)
    def _internal(exc):
        log("http.unhandled_error", error=type(exc).__name__)
        return _err(500, "INTERNAL_ERROR", "Erro inesperado. Tente novamente.")

    # ================================================================== helpers
    def _json_body():
        data, err = parse_json_object(request.get_data(as_text=True))
        return (None, _err(err.status, err.code, err.message)) if err else (data, None)

    def _owned(conv_id):
        return store.get_owned(conv_id, g.user, ignore_owner="idor" in faults)

    def _not_found():
        return _err(404, "CONVERSATION_NOT_FOUND", "Conversa não encontrada.")

    # ================================================================== frontend
    @app.get("/")
    def _index():
        return send_from_directory(STATIC_DIR, "index.html")

    @app.get("/config.js")
    def _ui_config():
        ui_faults = sorted(f for f in faults if f.startswith("ui_"))
        return Response(f"window.LYNN_CONFIG = {json.dumps({'faults': ui_faults})};",
                        mimetype="application/javascript")

    # ================================================================== API
    @app.post("/api/v1/conversations")
    def create_conversation():
        data, err = _json_body()
        if err:
            return err
        verr = validate_agent(data.get("agent_id"))
        if verr:
            return _err(422, verr.code, verr.message)
        conv = store.create(g.user, data["agent_id"])
        log("conversation.created", conversation_id=conv["id"], user_id=g.user, agent_id=conv["agent_id"])
        return jsonify(store.snapshot(conv)), 201

    @app.get("/api/v1/conversations/<conv_id>")
    def get_conversation(conv_id):
        conv = _owned(conv_id)
        return (jsonify(store.snapshot(conv)), 200) if conv else _not_found()

    @app.post("/api/v1/conversations/<conv_id>/close")
    def close_conversation(conv_id):
        conv = _owned(conv_id)
        if conv is None:
            return _not_found()
        if store.close(conv):
            log("conversation.closed", conversation_id=conv_id, user_id=g.user)
        return jsonify(store.snapshot(conv)), 200

    @app.post("/api/v1/conversations/<conv_id>/messages")
    def send_message(conv_id):
        # Ordem das checagens (P-11): auth → JSON → dono (404) → encerrada (409) → validação → idempotência
        data, err = _json_body()
        if err:
            return err
        conv = _owned(conv_id)
        if conv is None:
            return _not_found()
        if conv["status"] == "closed" and "allow_closed" not in faults:
            return _err(409, "CONVERSATION_CLOSED", CLOSED_MSG)
        max_len = MAX_CONTENT - 1 if "off_by_one_limit" in faults else MAX_CONTENT
        content, verr = validate_content(data.get("content"), max_len)
        if verr:
            return _err(422, verr.code, verr.message)

        key = None if "no_idempotency" in faults else request.headers.get("Idempotency-Key")
        fingerprint = hashlib.sha256(content.encode()).hexdigest()
        scope = (g.user, conv_id, key) if key else None
        retry_msg_id = None
        if scope:
            begin = idem.begin(scope, fingerprint)
            if begin.decision is Decision.KEY_REUSED:
                return _err(409, "IDEMPOTENCY_KEY_REUSED", "Idempotency-Key já usada com outro conteúdo.")
            if begin.decision is Decision.IN_PROGRESS:
                return _err(409, "IDEMPOTENCY_IN_PROGRESS", "Mensagem já está sendo processada.", {"Retry-After": "1"})
            if begin.decision is Decision.REPLAY:
                log("idempotency.replay", conversation_id=conv_id, idempotency_key=key)
                status, body = begin.record.response
                return jsonify(body), status, {"Idempotent-Replayed": "true"}
            if begin.decision is Decision.RETRY_FAILED:
                retry_msg_id = begin.record.user_message_id
        try:
            return _process(conv, content, fingerprint, key, scope, retry_msg_id)
        except Exception:
            if scope:  # erro inesperado não pode travar a chave em in_progress
                idem.fail(scope)
            raise

    def _process(conv, content, fingerprint, key, scope, retry_msg_id):
        conv_id = conv["id"]
        with store.conversation_lock(conv_id):
            # Revalida DENTRO do lock: um close concorrente pode ter ocorrido enquanto esperava.
            if conv["status"] == "closed" and not faults & {"allow_closed", "stale_closed_check"}:
                if scope:
                    idem.release(scope)
                return _err(409, "CONVERSATION_CLOSED", CLOSED_MSG)
            user_msg = store.reusable_failed_message(conv, retry_msg_id) or store.append_user_message(conv, content)
            context = (store.all_message_contents() if "context_leak" in faults
                       else store.llm_context(conv, exclude=user_msg))
            log("message.received", conversation_id=conv_id, user_id=g.user, message_id=user_msg["id"],
                content_len=len(content), content_sha256=fingerprint[:12], idempotency_key=key)
            try:
                # Timeout imposto pela APLICAÇÃO, independente do provedor.
                result = _LLM_POOL.submit(llm.generate, context, content).result(timeout=llm.settings.timeout_ms / 1000)
            except Exception as exc:
                user_msg["status"] = "failed"
                if scope:
                    idem.fail(scope, user_msg["id"])
                if not isinstance(exc, (LLMUnavailable, FutureTimeout)):
                    raise  # bug inesperado → 500 padronizado, mensagem e chave preservadas
                timeout = isinstance(exc, FutureTimeout)
                log("llm.failure", conversation_id=conv_id, message_id=user_msg["id"],
                    kind="timeout" if timeout else "unavailable", detail=str(exc) or "timeout")
                if "silent_llm_failure" in faults:
                    fake = {"id": "msg_" + uuid.uuid4().hex[:16], "seq": user_msg["seq"] + 1, "role": "assistant",
                            "content": "", "status": "completed", "created_at": now_iso(),
                            "reply_to": user_msg["id"], "metadata": None, "feedback": None}
                    return jsonify({"user_message": user_msg, "assistant_message": fake}), 201
                fail = llm_failure_response(timed_out=timeout)
                return _err(fail.status, fail.code, fail.message, {"Retry-After": str(fail.retry_after_s)})

            guard = (apply_output_guardrail(result.content, result.finish_reason, SYSTEM_CANARY)
                     if "guardrail_off" not in faults else apply_output_guardrail(result.content, result.finish_reason, ""))
            if guard.blocked_rule:
                log("guardrail.blocked", conversation_id=conv_id, message_id=user_msg["id"], rule=guard.blocked_rule)
            user_msg["status"] = "completed"
            assistant = store.append_assistant_message(conv, user_msg, guard.text, {
                "model": result.model, "latency_ms": result.latency_ms, "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens, "finish_reason": guard.finish_reason})
            body = {"user_message": dict(user_msg), "assistant_message": assistant}
            if scope:
                idem.complete(scope, (201, body))
            log("message.answered", conversation_id=conv_id, message_id=assistant["id"],
                latency_ms=result.latency_ms, prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens, finish_reason=guard.finish_reason)
        return jsonify(body), 201

    @app.post("/api/v1/conversations/<conv_id>/messages/<message_id>/feedback")
    def give_feedback(conv_id, message_id):
        data, err = _json_body()
        if err:
            return err
        conv = _owned(conv_id)
        if conv is None:
            return _not_found()
        msg = store.find_message(conv, message_id)
        if msg is None:
            return _err(404, "MESSAGE_NOT_FOUND", "Mensagem não encontrada.")
        if not can_receive_feedback(msg):
            return _err(422, "FEEDBACK_NOT_ALLOWED", "Só respostas do agente podem ser avaliadas.")
        parsed, verr = validate_feedback(data)
        if verr:
            return _err(422, verr.code, verr.message)
        if "feedback_first_wins" in faults and msg.get("feedback"):
            fb = dict(msg["feedback"])  # defeito: mantém a primeira avaliação (viola RN04)
        else:
            fb = store.set_feedback(msg, *parsed)
        log("feedback.recorded", conversation_id=conv_id, message_id=message_id, user_id=g.user,
            rating=fb["rating"], comment_len=len(fb["comment"] or ""))  # nunca o texto do comentário
        return jsonify({"message_id": message_id, **fb}), 200

    # ================================================================== controle de teste
    if test_control:
        @app.post("/__test__/reset")
        def _reset():
            store.reset()
            idem.clear()
            idem.ttl_s = default_ttl  # reset completo: config alterada por um cenário não vaza para o próximo
            llm.reset()
            log_buffer.clear()
            return jsonify({"ok": True})

        @app.post("/__test__/llm")
        def _llm_mode():
            data = request.get_json(force=True, silent=True) or {}
            for k in ("mode", "delay_ms", "timeout_ms"):
                if k in data:
                    setattr(llm.settings, k, data[k])
            return jsonify(vars(llm.settings))

        @app.post("/__test__/config")
        def _config():
            data = request.get_json(force=True, silent=True) or {}
            if "idempotency_ttl_s" in data:
                idem.ttl_s = int(data["idempotency_ttl_s"])
            return jsonify({"idempotency_ttl_s": idem.ttl_s})

        @app.get("/__test__/stats")
        def _stats():
            return jsonify({"llm_calls": llm.calls, "faults": sorted(faults)})

        @app.get("/__test__/logs")
        def _logs():
            return jsonify(list(log_buffer))

    return app
