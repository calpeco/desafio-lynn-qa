"""Steps de ambiente (LLM simulado, idempotência) e asserções genéricas de resposta HTTP."""
import time

from behave import given, step, then

from qa_support.contracts import assert_error, assert_matches


# ---------------------------------------------------------------- ambiente
@given("que a API de conversas está disponível")
def api_available(context):
    # o reset já foi feito no before_scenario; aqui confirmamos o estado limpo e o LLM saudável
    assert context.control.stats()["llm_calls"] == 0


@given('que o modelo de linguagem está no modo "{mode:Q}" com atraso de {delay:d} ms e timeout de {timeout:d} ms')
def llm_mode_delay(context, mode, delay, timeout):
    context.control.llm(mode, delay_ms=delay, timeout_ms=timeout)


@given('que o modelo de linguagem está no modo "{mode:Q}"')
def llm_mode(context, mode):
    context.control.llm(mode)


@given("que o modelo de linguagem responde em {delay:d} ms com timeout de {timeout:d} ms")
def llm_slow(context, delay, timeout):
    context.control.llm("slow", delay_ms=delay, timeout_ms=timeout)


@given("que o modelo de linguagem volta a funcionar")
def llm_recovers_given(context):
    context.control.llm("ok")


@step("o modelo de linguagem volta a funcionar")
def llm_recovers(context):
    context.control.llm("ok")


@given("que a validade das chaves de idempotência é de {seconds:d} segundos")
def idem_ttl(context, seconds):
    context.control.config(idempotency_ttl_s=seconds)


@step('"{persona:Q}" aguarda {ms:d} ms')
def wait_ms(context, persona, ms):  # persona só dá legibilidade ao Gherkin
    time.sleep(ms / 1000)


# ---------------------------------------------------------------- asserções HTTP
@then("a resposta tem status {status:d}")
def status_is(context, status):
    r = context.response
    assert r.status_code == status, f"esperado {status}, obtido {r.status_code}: {r.text[:300]}"


@then('a resposta tem status {status:d} e código de erro "{code:Q}"')
def error_is(context, status, code):
    assert_error(context.response, status, code)


@given('que a última resposta teve status {status:d} e código de erro "{code:Q}"')
def last_error_was(context, status, code):
    assert_error(context.response, status, code)


@then('a resposta segue o contrato "{name:Q}"')
def follows_contract(context, name):
    assert_matches(name, context.response.json())


@then("a resposta tem Content-Type JSON")
def content_type_json(context):
    assert context.response.headers["content-type"].startswith("application/json")


@then('a resposta tem o cabeçalho "{header:Q}" igual a "{value:Q}"')
def header_equals(context, header, value):
    assert context.response.headers.get(header) == value, dict(context.response.headers)


@then('a resposta tem o cabeçalho "{header:Q}" preenchido')
def header_present(context, header):
    assert context.response.headers.get(header), f"cabeçalho {header} ausente/vazio"


@then('a resposta não tem o cabeçalho "{header:Q}"')
def header_absent(context, header):
    assert header not in context.response.headers, dict(context.response.headers)


@then('a mensagem de erro para o usuário contém "{text:Q}"')
def error_message_contains(context, text):
    msg = context.response.json()["error"]["message"]
    assert text.lower() in msg.lower(), msg


@then("a resposta orienta tentar novamente depois")
def has_retry_after(context):
    assert int(context.response.headers["retry-after"]) > 0


@then("a resposta chegou em menos de {ms:d} ms")
def responded_within(context, ms):
    elapsed = context.response.elapsed.total_seconds() * 1000
    assert elapsed < ms, f"{elapsed:.0f} ms"


@then('a resposta não expõe "{text:Q}"')
def does_not_expose(context, text):
    assert text not in context.response.text, f"vazou {text!r}"


@then("o corpo da resposta contém apenas o objeto de erro")
def only_error_body(context):
    assert set(context.response.json()) == {"error"}, context.response.text


@then("o modelo de linguagem foi chamado {n:d} vez(es)")
def llm_calls(context, n):
    calls = context.control.stats()["llm_calls"]
    assert calls == n, f"LLM chamado {calls} vez(es); esperado {n} (custo/duplicidade)"


@then("a latência reportada pelo agente é de pelo menos {ms:d} ms")
def reported_latency(context, ms):
    # tolerância embutida no valor do cenário (770 para 800 ms) cobre relógio de baixa resolução
    latency = context.response.json()["assistant_message"]["metadata"]["latency_ms"]
    assert latency >= ms, f"latência reportada {latency} ms"
