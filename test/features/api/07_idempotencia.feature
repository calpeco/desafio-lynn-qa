# language: pt
@api @idempotency
Funcionalidade: Reenvio, duplo clique e idempotência
  Ver docs/ANALISE_DE_FALHA.md (Parte C).
  Premissa P-3: Idempotency-Key opcional, com escopo (usuário, conversa, chave) e TTL.
  Risco: mensagens e respostas duplicadas, tokens em dobro e contexto do LLM contaminado.

  Contexto:
    Dado que a API de conversas está disponível
    E que "Alice" tem uma conversa aberta

  @smoke @CONV-RN09 @R02
  Cenário: Reenvio após perda da resposta (falha de rede) não duplica
    Dado que "Alice" enviou com a chave "k1" a mensagem "Qual o horário?"
    Quando "Alice" envia com a chave "k1" a mensagem "Qual o horário?"
    Então a resposta tem status 201
    E a resposta tem o cabeçalho "Idempotent-Replayed" igual a "true"
    E a resposta é idêntica à da primeira tentativa
    E o histórico de "Alice" tem 2 mensagens
    E o modelo de linguagem foi chamado 1 vez(es)

  @smoke @CONV-RN09 @R02
  Cenário: Duplo clique simultâneo gera uma única mensagem e uma única resposta
    Dado que o modelo de linguagem responde em 400 ms com timeout de 5000 ms
    Quando "Alice" clica duas vezes em enviar "clique duplo" com a chave "k1"
    Então um envio foi aceito e o outro foi um replay ou recusado como em andamento
    E o histórico contém, em ordem:
      | papel     | conteúdo     | status    |
      | user      | clique duplo | completed |
      | assistant | *            | completed |
    E o modelo de linguagem foi chamado 1 vez(es)

  @CONV-RN09 @R02
  Cenário: Reenvio após falha do LLM reaproveita a mensagem do usuário
    Dado que o modelo de linguagem está no modo "error"
    E que "Alice" enviou com a chave "k1" a mensagem "me ajuda"
    Quando o modelo de linguagem volta a funcionar
    E "Alice" envia com a chave "k1" a mensagem "me ajuda"
    Então a resposta tem status 201
    E o histórico contém, em ordem:
      | papel     | conteúdo | status    |
      | user      | me ajuda | completed |
      | assistant | *        | completed |

  @CONV-RN09 @R02
  Cenário: Mesma chave com conteúdo diferente é rejeitada
    Dado que "Alice" enviou com a chave "k1" a mensagem "texto A"
    Quando "Alice" envia com a chave "k1" a mensagem "texto B"
    Então a resposta tem status 409 e código de erro "IDEMPOTENCY_KEY_REUSED"
    E o histórico de "Alice" tem 2 mensagens

  @CONV-RN09 @R02
  Cenário: Chaves diferentes são mensagens legitimamente distintas (controle negativo)
    Quando "Alice" envia com a chave "k1" a mensagem "ok"
    E "Alice" envia com a chave "k2" a mensagem "ok"
    Então o histórico de "Alice" tem 4 mensagens

  @CONV-RN09 @R02
  Cenário: A chave tem escopo por pessoa e por conversa
    Dado que "Alice" tem uma conversa aberta chamada "segunda"
    E que "Bob" tem uma conversa aberta chamada "do bob"
    Quando "Alice" envia com a chave "mesma" a mensagem "segredo"
    E "Alice" envia na conversa "segunda" com a chave "mesma" a mensagem "segredo"
    E "Bob" envia na conversa "do bob" com a chave "mesma" a mensagem "segredo"
    Então nenhum dos três envios foi um replay e todos geraram mensagens distintas

  @CONV-RN09 @R02
  Cenário: Reenvio após falha, com a conversa já adiantada, abre um novo turno sem quebrar a ordem
    Dado que o modelo de linguagem está no modo "error"
    E que "Alice" enviou com a chave "k1" a mensagem "q1"
    E que o modelo de linguagem volta a funcionar
    E que "Alice" enviou com a chave "k2" a mensagem "q2"
    Quando "Alice" envia com a chave "k1" a mensagem "q1"
    Então a resposta tem status 201
    E o histórico contém, em ordem:
      | papel     | conteúdo | status    |
      | user      | q1       | failed    |
      | user      | q2       | completed |
      | assistant | *        | completed |
      | user      | q1       | completed |
      | assistant | *        | completed |
    E cada resposta do agente vem logo após a sua pergunta

  @CONV-RN09 @R02
  Cenário: Sem chave, o reenvio cria nova mensagem (limite conhecido; a correção depende do cliente)
    Dado que o modelo de linguagem está no modo "error"
    E que "Alice" enviou a mensagem "sem chave"
    Quando o modelo de linguagem volta a funcionar
    E "Alice" envia a mensagem "sem chave"
    Então o histórico contém, em ordem:
      | papel     | conteúdo  | status    |
      | user      | sem chave | failed    |
      | user      | sem chave | completed |
      | assistant | *         | completed |

  @CONV-RN09 @R02
  Cenário: Erro inesperado (500) não trava a chave nem perde a mensagem
    Dado que o modelo de linguagem está no modo "crash"
    E que "Alice" enviou com a chave "k1" a mensagem "oi"
    E que a última resposta teve status 500 e código de erro "INTERNAL_ERROR"
    Quando o modelo de linguagem volta a funcionar
    E "Alice" envia com a chave "k1" a mensagem "oi"
    Então a resposta tem status 201
    E o histórico contém, em ordem:
      | papel     | conteúdo | status    |
      | user      | oi       | completed |
      | assistant | *        | completed |

  @CONV-RN09 @R02
  Cenário: Chave expirada (TTL) é tratada como nova
    Dado que a validade das chaves de idempotência é de 0 segundos
    E que "Alice" enviou com a chave "k1" a mensagem "oi"
    Quando "Alice" aguarda 50 ms
    E "Alice" envia com a chave "k1" a mensagem "oi"
    Então a resposta tem status 201
    E a resposta não tem o cabeçalho "Idempotent-Replayed"
    E o histórico de "Alice" tem 4 mensagens
