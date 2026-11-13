"""Unit: estado da conversa, ordem (seq) e regra de reaproveitamento de mensagem que falhou (P-8)."""
import pytest

from lynn_mock.domain.conversations import ConversationStore


def _store_with_conv():
    s = ConversationStore()
    return s, s.create("u_alice", "agt_support")


@pytest.mark.trace("CONV-RN05", "R10")
def test_seq_e_contiguo_e_reply_to_aponta_a_pergunta():
    s, c = _store_with_conv()
    u = s.append_user_message(c, "oi")
    a = s.append_assistant_message(c, u, "olá", {})
    assert (u["seq"], a["seq"], a["reply_to"]) == (1, 2, u["id"])


@pytest.mark.trace("CONV-RN08", "R01")
def test_conversa_alheia_e_inexistente_sao_none():
    s, c = _store_with_conv()
    assert s.get_owned(c["id"], "u_bob") is None
    assert s.get_owned("conv_nope", "u_alice") is None
    assert s.get_owned(c["id"], "u_bob", ignore_owner=True) is c   # caminho do defeito `idor`


@pytest.mark.trace("CONV-RN03", "R08")
def test_close_e_idempotente():
    s, c = _store_with_conv()
    assert s.close(c) is True
    closed_at = c["closed_at"]
    assert s.close(c) is False and c["closed_at"] == closed_at


@pytest.mark.trace("CONV-RN05", "CONV-RN09", "R02")
def test_mensagem_falha_so_e_reaproveitada_se_for_a_ultima():
    s, c = _store_with_conv()
    failed = s.append_user_message(c, "q1")
    failed["status"] = "failed"
    assert s.reusable_failed_message(c, failed["id"]) is failed
    s.append_user_message(c, "q2")
    assert s.reusable_failed_message(c, failed["id"]) is None


@pytest.mark.trace("CONV-RN11", "R05")
def test_contexto_do_llm_ignora_mensagens_falhas_e_a_atual():
    s, c = _store_with_conv()
    ok = s.append_user_message(c, "ok")
    bad = s.append_user_message(c, "falhou")
    bad["status"] = "failed"
    current = s.append_user_message(c, "atual")
    assert s.llm_context(c, exclude=current) == [ok["content"]]


@pytest.mark.trace("CONV-RN05")
def test_snapshot_nao_expoe_referencias_internas():
    s, c = _store_with_conv()
    s.append_user_message(c, "oi")
    snap = s.snapshot(c)
    snap["messages"][0]["content"] = "alterado"
    assert c["messages"][0]["content"] == "oi"


@pytest.mark.trace("CONV-RN05", "R10")
def test_append_concorrente_mantem_seq_unico_e_contiguo():
    import threading

    s, c = _store_with_conv()
    barrier = threading.Barrier(40)

    def worker(i):
        barrier.wait()
        s.append_user_message(c, f"m{i}")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(40)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(m["seq"] for m in c["messages"]) == list(range(1, 41))
