# language: pt
# Gerado por test/scripts/qa_scaffold.py a partir de feedback-resposta.md e completado pelo agent-qa-lynn.
# Rastreabilidade: @FDBK-RNxx (regras) e @Rxx (riscos). Regras puras também em tests/unit/test_feedback.py.
@api @fdbk
Funcionalidade: Avaliação de respostas do agente
  Spec: test/specs/feedback-resposta.md
  A pessoa avalia cada resposta do agente com positive/negative e um comentário opcional.
  Riscos: avaliação em mensagem errada ou alheia (R01), duplicidade (R02), validação (R09),
  PII em logs (R12) e quebra de contrato do histórico (R17).

  Contexto:
    Dado que a API de conversas está disponível
    E que "Alice" tem uma conversa aberta
    E que "Alice" enviou a mensagem "Qual o horário de atendimento?"

  # ---------------------------------------------------------------- RN07 (critério da spec)
  @smoke @FDBK-RN07 @R17
  Cenário: Avaliar positivamente uma resposta do agente
    Quando "Alice" avalia a última resposta do agente como "positive" com o comentário "Resposta clara"
    Então a resposta tem status 200
    E a resposta segue o contrato "feedback_response"
    E a última resposta do agente no histórico tem avaliação "positive" com o comentário "Resposta clara"

  @FDBK-RN07 @R17
  Cenário: O histórico traz exatamente a avaliação registrada e não ganha mensagens novas
    Quando "Alice" avalia a última resposta do agente como "negative"
    Então a resposta tem status 200
    E a resposta registra a avaliação "negative" sem comentário
    E a avaliação no histórico é a mesma devolvida pela API
    E as mensagens do usuário no histórico não têm avaliação
    E o histórico de "Alice" tem 2 mensagens

  # ---------------------------------------------------------------- RN01
  @FDBK-RN01 @R09
  Cenário: Mensagem da pessoa usuária não pode ser avaliada
    Quando "Alice" avalia a última mensagem do usuário como "positive"
    Então a resposta tem status 422 e código de erro "FEEDBACK_NOT_ALLOWED"
    E as mensagens do usuário no histórico não têm avaliação

  # ---------------------------------------------------------------- RN02
  @FDBK-RN02 @R09
  Cenário: As duas avaliações válidas são aceitas
    Quando "Alice" avalia a última resposta do agente como "positive"
    Então a resposta registra a avaliação "positive" sem comentário
    Quando "Alice" avalia a última resposta do agente como "negative"
    Então a resposta registra a avaliação "negative" sem comentário

  @FDBK-RN02 @R09
  Esquema do Cenário: Avaliação ausente, inválida ou de outro tipo é rejeitada (<caso>)
    Quando "Alice" avalia a última resposta do agente com o corpo <corpo>
    Então a resposta tem status 422 e código de erro "VALIDATION_ERROR"
    E a última resposta do agente na conversa de "Alice" não tem avaliação

    Exemplos:
      | caso                 | corpo                                   |
      | ausente              | {"comment": "sem nota"}                 |
      | fora do domínio      | {"rating": "neutral"}                   |

  @FDBK-RN02 @FDBK-RN04 @R09
  Cenário: Avaliação inválida não apaga a avaliação anterior
    Dado que "Alice" avaliou a última resposta do agente como "positive" com o comentário "boa"
    Quando "Alice" avalia a última resposta do agente com o corpo {"rating": "meh"}
    Então a resposta tem status 422 e código de erro "VALIDATION_ERROR"
    E a última resposta do agente no histórico tem avaliação "positive" com o comentário "boa"

  # ---------------------------------------------------------------- RN03
  @FDBK-RN03 @R09
  Esquema do Cenário: Comentário dentro do limite é aceito (<caso>)
    Quando "Alice" avalia a última resposta do agente como "negative" com um comentário de <tamanho> caracteres "<caractere>"
    Então a resposta tem status 200
    E a resposta registra o comentário enviado sem os espaços das bordas

    Exemplos:
      | caso                | tamanho | caractere |
      | limite superior     | 500     | a         |

  @FDBK-RN03 @R09
  Cenário: Comentário acima de 500 caracteres é rejeitado
    Quando "Alice" avalia a última resposta do agente como "negative" com um comentário de 501 caracteres "a"
    Então a resposta tem status 422 e código de erro "VALIDATION_ERROR"
    E a última resposta do agente na conversa de "Alice" não tem avaliação

  @FDBK-RN03 @R09
  Esquema do Cenário: Comentário vazio ou só com espaços equivale a sem comentário (<caso>)
    Quando "Alice" avalia a última resposta do agente com o corpo <corpo>
    Então a resposta tem status 200
    E a resposta registra a avaliação "positive" sem comentário
    E a última resposta do agente no histórico tem avaliação "positive" sem comentário

    Exemplos:
      | caso           | corpo                                        |
      | só espaços     | {"rating": "positive", "comment": "     "}       |

  # ---------------------------------------------------------------- RN04
  @FDBK-RN04 @R02
  Cenário: Avaliar de novo substitui a avaliação anterior, inclusive o comentário
    Dado que "Alice" avaliou a última resposta do agente como "positive" com o comentário "Resposta clara"
    Quando "Alice" avalia a última resposta do agente como "negative"
    Então a resposta tem status 200
    E a resposta registra a avaliação "negative" sem comentário
    E a última resposta do agente no histórico tem avaliação "negative" sem comentário
    E o histórico de "Alice" tem 2 mensagens

  @FDBK-RN04 @R02
  Cenário: Repetir a mesma avaliação não duplica nada
    Dado que "Alice" avaliou a última resposta do agente como "positive" com o comentário "ok"
    Quando "Alice" avalia a última resposta do agente como "positive" com o comentário "ok"
    Então a resposta tem status 200
    E a avaliação no histórico é a mesma devolvida pela API
    E o histórico de "Alice" tem 2 mensagens

  # ---------------------------------------------------------------- RN05 (critério da spec + bordas)
  @security @FDBK-RN05 @R01
  Cenário: Outra pessoa não avalia resposta em conversa alheia
    Quando "Bob" avalia a última resposta do agente na conversa de "Alice" como "negative"
    Então a resposta tem status 404 e código de erro "CONVERSATION_NOT_FOUND"
    E a última resposta do agente na conversa de "Alice" não tem avaliação

  @security @FDBK-RN05 @R01
  Cenário: Resposta alheia não pode ser avaliada pela conversa da própria pessoa
    Dado que "Bob" tem uma conversa aberta
    Quando "Bob" avalia, na própria conversa, a última resposta do agente da conversa de "Alice"
    Então a resposta tem status 404 e código de erro "MESSAGE_NOT_FOUND"
    E a última resposta do agente na conversa de "Alice" não tem avaliação

  @security @FDBK-RN05 @R01
  Cenário: Conversa inexistente retorna CONVERSATION_NOT_FOUND
    Quando "Alice" avalia uma mensagem de uma conversa inexistente
    Então a resposta tem status 404 e código de erro "CONVERSATION_NOT_FOUND"

  @FDBK-RN05 @R01
  Cenário: Mensagem inexistente retorna MESSAGE_NOT_FOUND
    Quando "Alice" avalia uma mensagem inexistente da própria conversa
    Então a resposta tem status 404 e código de erro "MESSAGE_NOT_FOUND"

  @security @FDBK-RN05 @R01
  Cenário: Avaliar exige autenticação
    Quando uma requisição sem autenticação avalia a última resposta do agente de "Alice"
    Então a resposta tem status 401 e código de erro "UNAUTHENTICATED"
    E a última resposta do agente na conversa de "Alice" não tem avaliação

  # ---------------------------------------------------------------- RN06
  @FDBK-RN06
  Cenário: Resposta de conversa encerrada pode ser avaliada
    Dado que "Alice" encerrou a conversa
    Quando "Alice" avalia a última resposta do agente como "negative" com o comentário "demorou"
    Então a resposta tem status 200
    E a resposta segue o contrato "feedback_response"
    E a última resposta do agente no histórico tem avaliação "negative" com o comentário "demorou"
    Quando "Alice" consulta a conversa
    Então a conversa está encerrada

  # ---------------------------------------------------------------- RN08
  @security @FDBK-RN08 @R12
  Cenário: Comentário com dado pessoal não vai para os logs
    Quando "Alice" avalia a última resposta do agente como "negative" com o comentário "Meu CPF é 123.456.789-00, me liguem"
    Então a resposta tem status 200
    E o evento de log "feedback.recorded" contém os campos "message_id;rating;comment_len"
    E os logs não contêm "123.456.789-00;me liguem"

  @security @FDBK-RN08 @R12
  Cenário: Comentário rejeitado com dado pessoal também não vai para os logs
    Quando "Alice" avalia a última resposta do agente com o corpo {"rating": "talvez", "comment": "CPF 987.654.321-00"}
    Então a resposta tem status 422 e código de erro "VALIDATION_ERROR"
    E os logs não contêm "987.654.321-00"
