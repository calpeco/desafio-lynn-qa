# Catálogo de steps

> Gerado por `python test/scripts/step_catalog.py`. **Não edite à mão.** Antes de criar um passo novo,
> procure aqui. Tipos de placeholder: `{x:Q}` texto entre aspas · `{n:d}` inteiro · `{x}` resto da linha.
> Passos `Dado` começam com `que` no texto (ex.: `Dado que "Alice" tem uma conversa aberta`).

Total: **130 passos** em 9 arquivos.

## `test/features/steps/common_steps.py`

| Tipo | Padrão | Função |
|---|---|---|
| Dado | `que a API de conversas está disponível` | `api_available` (L11) |
| Dado | `que o modelo de linguagem está no modo "{mode:Q}" com atraso de {delay:d} ms e timeout de {timeout:d} ms` | `llm_mode_delay` (L17) |
| Dado | `que o modelo de linguagem está no modo "{mode:Q}"` | `llm_mode` (L22) |
| Dado | `que o modelo de linguagem responde em {delay:d} ms com timeout de {timeout:d} ms` | `llm_slow` (L27) |
| Dado | `que o modelo de linguagem volta a funcionar` | `llm_recovers_given` (L32) |
| Dado/Quando/Então | `o modelo de linguagem volta a funcionar` | `llm_recovers` (L37) |
| Dado | `que a validade das chaves de idempotência é de {seconds:d} segundos` | `idem_ttl` (L42) |
| Dado/Quando/Então | `"{persona:Q}" aguarda {ms:d} ms` | `wait_ms` (L47) |
| Então | `a resposta tem status {status:d}` | `status_is` (L53) |
| Então | `a resposta tem status {status:d} e código de erro "{code:Q}"` | `error_is` (L59) |
| Dado | `que a última resposta teve status {status:d} e código de erro "{code:Q}"` | `last_error_was` (L64) |
| Então | `a resposta segue o contrato "{name:Q}"` | `follows_contract` (L69) |
| Então | `a resposta tem Content-Type JSON` | `content_type_json` (L74) |
| Então | `a resposta tem o cabeçalho "{header:Q}" igual a "{value:Q}"` | `header_equals` (L79) |
| Então | `a resposta tem o cabeçalho "{header:Q}" preenchido` | `header_present` (L84) |
| Então | `a resposta não tem o cabeçalho "{header:Q}"` | `header_absent` (L89) |
| Então | `a mensagem de erro para o usuário contém "{text:Q}"` | `error_message_contains` (L94) |
| Então | `a resposta orienta tentar novamente depois` | `has_retry_after` (L100) |
| Então | `a resposta chegou em menos de {ms:d} ms` | `responded_within` (L105) |
| Então | `a resposta não expõe "{text:Q}"` | `does_not_expose` (L111) |
| Então | `o corpo da resposta contém apenas o objeto de erro` | `only_error_body` (L116) |
| Então | `o modelo de linguagem foi chamado {n:d} vez(es)` | `llm_calls` (L121) |
| Então | `a latência reportada pelo agente é de pelo menos {ms:d} ms` | `reported_latency` (L127) |

## `test/features/steps/conversation_steps.py`

| Tipo | Padrão | Função |
|---|---|---|
| Dado | `que "{owner:Q}" tem uma conversa aberta` | `has_open_conversation` (L15) |
| Dado | `que "{owner:Q}" tem uma conversa aberta chamada "{name:Q}"` | `has_named_conversation` (L20) |
| Dado | `que "{persona:Q}" enviou a mensagem "{content:Q}"` | `has_sent` (L27) |
| Dado | `que "{persona:Q}" encerrou a conversa` | `has_closed` (L32) |
| Quando | `"{persona:Q}" cria uma conversa com o agente "{agent:Q}"` | `create_with_agent` (L40) |
| Quando | `"{persona:Q}" cria uma conversa com o corpo {body}` | `create_with_body` (L48) |
| Quando | `"{persona:Q}" envia a mensagem "{content:Q}"` | `send_message` (L53) |
| Quando | `"{persona:Q}" envia uma mensagem com {size:d} caracteres "{char:Q}"` | `send_sized` (L58) |
| Quando | `"{persona:Q}" envia o corpo {body}` | `send_raw_body` (L63) |
| Quando | `"{persona:Q}" envia o JSON malformado {raw}` | `send_malformed` (L68) |
| Quando | `"{persona:Q}" consulta a conversa` | `get_conversation` (L75) |
| Quando | `"{persona:Q}" encerra a conversa` | `close_conversation` (L80) |
| Quando | `"{persona:Q}" chama "{method:Q}" em "{path:Q}"` | `raw_call` (L85) |
| Quando | `"{persona:Q}" envia {n:d} mensagens em sequência` | `send_sequence` (L90) |
| Quando | `"{persona:Q}" envia {n:d} mensagens simultâneas` | `send_concurrently` (L97) |
| Quando | `"{persona:Q}" envia em segundo plano a mensagem "{content:Q}"` | `send_in_background` (L107) |
| Então | `a conversa está aberta, sem mensagens e pertence a "{owner_id:Q}"` | `conv_open_empty` (L120) |
| Então | `a conversa está encerrada` | `conv_closed` (L126) |
| Então | `a conversa de "{owner:Q}" continua aberta` | `conv_still_open` (L132) |
| Então | `a data de encerramento não mudou` | `closed_at_unchanged` (L138) |
| Então | `a resposta do agente referencia a mensagem enviada` | `assistant_replies_to_user` (L143) |
| Então | `a resposta do agente informa tokens de prompt e de resposta maiores que zero` | `has_token_metadata` (L149) |
| Então | `a mensagem do usuário não tem metadados` | `user_has_no_metadata` (L155) |
| Então | `o agente respondeu contendo "{text:Q}"` | `assistant_contains` (L160) |
| Então | `o conteúdo armazenado é igual ao enviado sem espaços nas bordas` | `stored_equals_sent` (L166) |
| Então | `o conteúdo armazenado é "{text:Q}"` | `stored_is` (L172) |
| Então | `nada foi persistido na conversa` | `nothing_persisted` (L177) |
| Então | `o histórico de "{owner:Q}" tem {n:d} mensagens` | `history_count` (L182) |
| Então | `o histórico contém, em ordem:` | `history_matches_table` (L188) |
| Então | `o histórico tem seq contíguo de 1 a {n:d}` | `seq_contiguous` (L199) |
| Então | `cada resposta do agente vem logo após a sua pergunta` | `replies_adjacent` (L204) |
| Então | `as mensagens do usuário estão na ordem em que foram enviadas` | `user_messages_in_order` (L213) |
| Então | `todos os envios simultâneos tiveram status 201` | `all_concurrent_ok` (L220) |
| Então | `o envio em segundo plano de "{content:Q}" terminou com status {status:d}` | `background_status` (L234) |
| Então | `o envio em segundo plano de "{content:Q}" terminou com status {status:d} e código de erro "{code:Q}"` | `background_error` (L239) |
| Então | `as mensagens do usuário no histórico são apenas "{content:Q}"` | `only_user_messages` (L244) |

## `test/features/steps/feedback_steps.py`

| Tipo | Padrão | Função |
|---|---|---|
| Dado | `que "{persona:Q}" avaliou a última resposta do agente como "{rating:Q}" com o comentário "{comment:Q}"` | `has_rated` (L49) |
| Quando | `"{persona:Q}" avalia a última resposta do agente como "{rating:Q}"` | `rate_last` (L56) |
| Quando | `"{persona:Q}" avalia a última resposta do agente como "{rating:Q}" com o comentário "{comment:Q}"` | `rate_last_with_comment` (L61) |
| Quando | `"{persona:Q}" avalia a última resposta do agente como "{rating:Q}" com um comentário de {n:d} caracteres "{char:Q}"` | `rate_last_sized` (L66) |
| Quando | `"{persona:Q}" avalia a última resposta do agente com o corpo {body}` | `rate_last_raw` (L72) |
| Quando | `"{persona:Q}" avalia a última resposta do agente na conversa de "{owner:Q}" como "{rating:Q}"` | `rate_others` (L77) |
| Quando | `"{persona:Q}" avalia, na própria conversa, a última resposta do agente da conversa de "{owner:Q}"` | `rate_foreign_message_in_own_conv` (L82) |
| Quando | `"{persona:Q}" avalia a última mensagem do usuário como "{rating:Q}"` | `rate_user_message` (L88) |
| Quando | `"{persona:Q}" avalia uma mensagem inexistente da própria conversa` | `rate_missing_message` (L94) |
| Quando | `"{persona:Q}" avalia uma mensagem de uma conversa inexistente` | `rate_in_missing_conversation` (L99) |
| Quando | `uma requisição sem autenticação avalia a última resposta do agente de "{owner:Q}"` | `rate_unauthenticated` (L104) |
| Então | `a resposta registra a avaliação "{rating:Q}" sem comentário` | `response_has_no_comment` (L116) |
| Então | `a resposta registra o comentário enviado sem os espaços das bordas` | `response_comment_trimmed` (L123) |
| Então | `a última resposta do agente no histórico tem avaliação "{rating:Q}" com o comentário "{comment:Q}"` | `history_has` (L130) |
| Então | `a última resposta do agente no histórico tem avaliação "{rating:Q}" sem comentário` | `history_has_no_comment` (L136) |
| Então | `a última resposta do agente na conversa de "{owner:Q}" não tem avaliação` | `history_without_feedback` (L142) |
| Então | `a avaliação no histórico é a mesma devolvida pela API` | `history_equals_response` (L148) |
| Então | `as mensagens do usuário no histórico não têm avaliação` | `user_messages_without_feedback` (L155) |

## `test/features/steps/feedback_ui_steps.py`

| Tipo | Padrão | Função |
|---|---|---|
| Dado/Quando/Então | `avalia na interface a última resposta do agente com {icon}` | `give_feedback_ui` (L14) |
| Então | `a interface agradece a avaliação` | `thanks_visible` (L19) |
| Então | `o botão {icon} da última resposta fica destacado` | `button_pressed` (L25) |
| Então | `cada resposta do agente mostra os botões 👍 e 👎 e as mensagens do usuário não` | `buttons_only_on_answers` (L33) |
| Então | `o texto das respostas do agente não inclui os botões de avaliação` | `text_without_buttons` (L46) |
| Então | `a interface fez {n:d} requisição(ões) de avaliação` | `feedback_request_count` (L52) |

## `test/features/steps/idempotency_steps.py`

| Tipo | Padrão | Função |
|---|---|---|
| Dado | `que "{persona:Q}" enviou com a chave "{key:Q}" a mensagem "{content:Q}"` | `has_sent_with_key` (L11) |
| Quando | `"{persona:Q}" envia com a chave "{key:Q}" a mensagem "{content:Q}"` | `send_with_key` (L16) |
| Quando | `"{persona:Q}" envia na conversa "{name:Q}" com a chave "{key:Q}" a mensagem "{content:Q}"` | `send_named_with_key` (L21) |
| Quando | `"{persona:Q}" clica duas vezes em enviar "{content:Q}" com a chave "{key:Q}"` | `double_click` (L28) — Dois POSTs disparados no mesmo instante (Barrier) com a mesma chave = duplo clique. |
| Então | `a resposta é idêntica à da primeira tentativa` | `same_as_first` (L47) |
| Então | `um envio foi aceito e o outro foi um replay ou recusado como em andamento` | `one_accepted` (L52) |
| Então | `nenhum dos três envios foi um replay e todos geraram mensagens distintas` | `scoped_keys` (L61) |

## `test/features/steps/llm_steps.py`

| Tipo | Padrão | Função |
|---|---|---|
| Quando | `"{persona:Q}" pergunta "{question:Q}" em {n:d} conversas novas` | `ask_n` (L20) |
| Quando | `"{persona:Q}" pergunta "{question:Q}" em uma conversa nova` | `ask_once` (L26) |
| Então | `todas as respostas respeitam as invariantes do agente` | `invariants` (L31) |
| Então | `todas as respostas contêm todos os termos "{raw:Q}"` | `contain_all` (L42) |
| Então | `todas as respostas contêm algum dos termos "{raw:Q}"` | `contain_any` (L49) |
| Então | `nenhuma resposta contém os termos "{raw:Q}"` | `contain_none` (L56) |
| Então | `há pelo menos {n:d} redações distintas` | `distinct_wordings` (L63) |
| Então | `o guardrail bloqueou e registrou {n:d} tentativas` | `guardrail_blocked` (L70) |
| Então | `os tokens de prompt crescem a cada turno` | `tokens_grow` (L79) |

## `test/features/steps/observability_steps.py`

| Tipo | Padrão | Função |
|---|---|---|
| Quando | `"{persona:Q}" envia a mensagem "{content:Q}" com o identificador de requisição "{rid:Q}"` | `send_with_request_id` (L8) |
| Quando | `"{persona:Q}" consulta a conversa "{raw_id:Q}" sem identificador de requisição` | `get_without_request_id` (L13) |
| Então | `os logs da requisição "{rid:Q}" contêm os eventos "{raw:Q}"` | `logs_have_events` (L18) |
| Então | `o evento de log "{event:Q}" contém os campos "{raw:Q}"` | `log_has_fields` (L25) |
| Então | `o evento de log "{event:Q}" da requisição "{rid:Q}" tem "{field:Q}" igual a "{value:Q}"` | `log_field_equals` (L33) |
| Então | `os logs não contêm "{raw:Q}"` | `logs_do_not_contain` (L39) |

## `test/features/steps/security_steps.py`

| Tipo | Padrão | Função |
|---|---|---|
| Quando | `uma requisição com autenticação "{auth:Q}" tenta "{action:Q}" na conversa de "{owner:Q}"` | `unauthenticated_attempt` (L16) |
| Quando | `"{persona:Q}" consulta a conversa de "{owner:Q}"` | `get_others_conversation` (L28) |
| Quando | `"{persona:Q}" envia a mensagem "{content:Q}" na conversa de "{owner:Q}"` | `send_to_others_conversation` (L33) |
| Quando | `"{persona:Q}" encerra a conversa de "{owner:Q}"` | `close_others_conversation` (L38) |
| Quando | `"{persona:Q}" consulta a conversa de "{owner:Q}" e uma conversa inexistente` | `compare_foreign_and_missing` (L43) |
| Quando | `"{persona:Q}" consulta a conversa "{raw_id:Q}"` | `get_by_raw_id` (L49) |
| Então | `as duas respostas são idênticas em status, código e mensagem` | `indistinguishable` (L54) |

## `test/features/steps/ui_steps.py`

| Tipo | Padrão | Função |
|---|---|---|
| Dado | `que "{persona:Q}" entrou no chat pela interface` | `logged_in` (L8) |
| Dado | `que a próxima resposta de envio de mensagem será perdida na rede` | `lose_next_response` (L15) — Simula a Parte C: a requisição CHEGA ao servidor (route.fetch), mas a resposta não |
| Dado/Quando/Então | `inicia na interface uma nova conversa com o "{agent:Q}"` | `start_conversation` (L32) |
| Dado/Quando/Então | `envia na interface a mensagem "{content:Q}"` | `send_ui` (L37) |
| Dado/Quando/Então | `digita na interface "{content:Q}" e clica duas vezes em Enviar` | `double_click_ui` (L42) |
| Dado/Quando/Então | `clica em "Tentar novamente" na interface` | `retry_ui` (L47) |
| Dado/Quando/Então | `encerra a conversa na interface` | `close_ui` (L52) |
| Então | `a interface mostra {users:d} mensagem(ns) do usuário e {assistants:d} do agente` | `ui_counts` (L57) |
| Então | `a última mensagem na interface é do agente e contém "{text:Q}"` | `last_is_assistant` (L65) |
| Então | `o campo de mensagem está vazio` | `input_empty` (L71) |
| Então | `a interface exibe o erro "{text:Q}"` | `ui_error` (L76) |
| Então | `a interface oferece "Tentar novamente"` | `retry_visible` (L82) |
| Então | `a interface não exibe erro` | `no_error` (L87) |
| Então | `a interface fez {n:d} requisição(ões) de envio de mensagem` | `ui_request_count` (L92) |
| Então | `a interface informa "{text:Q}"` | `ui_status` (L98) |
| Então | `o campo de mensagem e o botão Enviar estão desabilitados` | `composer_disabled` (L103) |
| Então | `a primeira mensagem do usuário aparece como o texto literal "{text:Q}"` | `literal_text` (L109) |
| Então | `nenhum diálogo JavaScript foi aberto` | `no_dialogs` (L115) |
