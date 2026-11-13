"""Unit: máquina de estados da idempotência (P-3, P-8). Relógio falso → testes determinísticos."""
import threading

import pytest

from lynn_mock.domain.idempotency import Decision, IdempotencyStore

pytestmark = pytest.mark.trace('CONV-RN09', 'R02')

SCOPE = ("u_alice", "conv_1", "k1")


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def store(clock):
    return IdempotencyStore(ttl_s=60, clock=clock)


def test_primeira_vez_processa(store):
    assert store.begin(SCOPE, "fp").decision is Decision.PROCEED


def test_em_andamento_bloqueia_segunda_requisicao(store):
    store.begin(SCOPE, "fp")
    assert store.begin(SCOPE, "fp").decision is Decision.IN_PROGRESS


def test_concluida_devolve_replay_com_a_mesma_resposta(store):
    store.begin(SCOPE, "fp")
    store.complete(SCOPE, (201, {"id": "x"}))
    r = store.begin(SCOPE, "fp")
    assert r.decision is Decision.REPLAY and r.record.response == (201, {"id": "x"})


def test_mesma_chave_com_outro_corpo_e_rejeitada(store):
    store.begin(SCOPE, "fp-a")
    store.complete(SCOPE, (201, {}))
    assert store.begin(SCOPE, "fp-b").decision is Decision.KEY_REUSED


def test_falha_permite_reprocessar_preservando_a_mensagem(store):
    store.begin(SCOPE, "fp")
    store.fail(SCOPE, "msg_1")
    r = store.begin(SCOPE, "fp")
    assert r.decision is Decision.RETRY_FAILED and r.record.user_message_id == "msg_1"


def test_fail_sem_id_nao_apaga_id_registrado(store):
    """Regressão encontrada na refatoração: o handler externo zerava o id e o reenvio duplicava."""
    store.begin(SCOPE, "fp")
    store.fail(SCOPE, "msg_1")
    store.begin(SCOPE, "fp")
    store.fail(SCOPE)
    assert store.begin(SCOPE, "fp").record.user_message_id == "msg_1"


def test_ttl_expirado_trata_como_nova(store, clock):
    store.begin(SCOPE, "fp")
    store.complete(SCOPE, (201, {}))
    clock.now += 61
    assert store.begin(SCOPE, "fp").decision is Decision.PROCEED


def test_ttl_no_limite_ainda_vale(store, clock):
    store.begin(SCOPE, "fp")
    store.complete(SCOPE, (201, {}))
    clock.now += 60
    assert store.begin(SCOPE, "fp").decision is Decision.REPLAY


def test_escopo_isola_usuario_e_conversa(store):
    store.begin(SCOPE, "fp")
    assert store.begin(("u_bob", "conv_1", "k1"), "fp").decision is Decision.PROCEED
    assert store.begin(("u_alice", "conv_2", "k1"), "fp").decision is Decision.PROCEED


def test_release_libera_a_chave(store):
    store.begin(SCOPE, "fp")
    store.release(SCOPE)
    assert store.begin(SCOPE, "fp").decision is Decision.PROCEED


def test_check_and_set_e_atomico_sob_concorrencia(store):
    """50 threads com a mesma chave: exatamente UMA pode processar (essência do anti duplo clique)."""
    barrier, decisions = threading.Barrier(50), []

    def worker():
        barrier.wait()
        decisions.append(store.begin(SCOPE, "fp").decision)

    threads = [threading.Thread(target=worker) for _ in range(50)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert decisions.count(Decision.PROCEED) == 1
    assert decisions.count(Decision.IN_PROGRESS) == 49
