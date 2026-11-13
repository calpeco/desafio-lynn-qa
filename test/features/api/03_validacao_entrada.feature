# language: pt
@api @functional @validation
Funcionalidade: Validação da mensagem e da criação de conversa
  Regra de negócio — o texto é obrigatório e tem entre 1 e 4.000 caracteres.
  Premissa P-5: conta code points Unicode após remover espaços das bordas.
  Risco: entrada inválida gerar erro 500, gastar tokens ou corromper o histórico.

  Contexto:
    Dado que a API de conversas está disponível
    E que "Alice" tem uma conversa aberta

  @CONV-RN04 @R09
  Esquema do Cenário: Tamanhos válidos nos limites são aceitos (<caso>)
    Quando "Alice" envia uma mensagem com <tamanho> caracteres "<caractere>"
    Então a resposta tem status 201
    E o conteúdo armazenado é igual ao enviado sem espaços nas bordas

    Exemplos:
      | caso                  | tamanho | caractere |
      | limite superior       | 4000    | a         |
      | emoji fora do BMP     | 4000    | 🙂        |

  @CONV-RN04 @R09
  Esquema do Cenário: Conteúdos especiais são armazenados sem alteração (<caso>)
    Quando "Alice" envia a mensagem "<conteúdo>"
    Então a resposta tem status 201
    E o conteúdo armazenado é igual ao enviado sem espaços nas bordas

    Exemplos:
      | caso                 | conteúdo                   |
      | SQL como texto       | '; DROP TABLE messages;--  |

  @CONV-RN04 @R09
  Esquema do Cenário: Conteúdo inválido é rejeitado sem consumir tokens (<caso>)
    Quando "Alice" envia o corpo <corpo>
    Então a resposta tem status 422 e código de erro "VALIDATION_ERROR"
    E o modelo de linguagem foi chamado 0 vez(es)
    E nada foi persistido na conversa

    Exemplos:
      | caso          | corpo                  |
      | vazio         | {"content": ""}        |
      | número        | {"content": 123}       |

  @CONV-RN04 @R09
  Cenário: Espaços nas bordas são removidos antes de armazenar e de contar o limite
    Quando "Alice" envia a mensagem "   texto com espaços   "
    Então a resposta tem status 201
    E o conteúdo armazenado é "texto com espaços"

  @CONV-RN04 @R09
  Cenário: 4001 caracteres é rejeitado (limite superior + 1)
    Quando "Alice" envia uma mensagem com 4001 caracteres "a"
    Então a resposta tem status 422 e código de erro "VALIDATION_ERROR"
    E nada foi persistido na conversa

  @CONV-RN04 @R09
  Esquema do Cenário: JSON malformado é rejeitado (<caso>)
    Quando "Alice" envia o JSON malformado <bruto>
    Então a resposta tem status 400 e código de erro "INVALID_JSON"

    Exemplos:
      | caso              | bruto              |
      | objeto incompleto | {"content": "x"    |

  @CONV-RN02 @R09
  Esquema do Cenário: Conversa exige agente válido (<caso>)
    Quando "Alice" cria uma conversa com o corpo <corpo>
    Então a resposta tem status 422 e código de erro "<código>"

    Exemplos:
      | caso         | corpo                          | código           |
      | desativado   | {"agent_id": "agt_retired"}     | AGENT_NOT_FOUND  |
      | nulo         | {"agent_id": null}              | VALIDATION_ERROR |
