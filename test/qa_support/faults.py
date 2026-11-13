"""Catálogo dos defeitos injetáveis (LYNN_FAULTS) e de onde a suíte deve detectá-los."""

# defeito: (descrição, tag da camada, feature que DEVE falhar)
FAULTS = {
    "no_idempotency": ("API ignora Idempotency-Key (bug da Parte C no servidor)", "@api", "07_idempotencia"),
    "idor": ("Não verifica o dono da conversa", "@api", "04_autenticacao_isolamento"),
    "allow_closed": ("Aceita mensagem em conversa encerrada", "@api", "05_ciclo_de_vida"),
    "stale_closed_check": ("Checa 'encerrada' fora do lock (corrida com close)", "@api", "05_ciclo_de_vida"),
    "guardrail_off": ("Sem filtro de saída: vaza o prompt de sistema", "@api", "08_comportamento_llm"),
    "context_leak": ("Contexto do LLM compartilhado entre conversas", "@api", "08_comportamento_llm"),
    "silent_llm_failure": ("Falha do LLM vira 201 com resposta vazia", "@api", "06_falhas_do_llm"),
    "off_by_one_limit": ("Rejeita exatamente 4000 caracteres", "@api", "03_validacao_entrada"),
    "feedback_first_wins": ("Nova avaliação não substitui a anterior (proposto pelo agent-qa-lynn)", "@api",
                            "10_avaliacao_de_respostas_do_agente"),
    "ui_double_submit": ("Frontend sem anti duplo clique e com nova chave no reenvio (bug da Parte C no cliente)",
                         "@ui", "chat_ui"),
}

# Defeitos que a suíte de SEGURANÇA (test/sec) também precisa detectar: defeito -> arquivo que deve falhar.
SEC_EXPECT = {
    "idor": "test_api1_bola",
    "guardrail_off": "test_llm01_prompt_injection",
    "context_leak": "test_llm02_divulgacao_sensivel",
}
