# language: pt
@api @security @smoke
Funcionalidade: Autenticação e isolamento entre pessoas usuárias
  Regras de negócio — apenas pessoas autenticadas criam/consultam conversas; ninguém acessa conversa alheia.
  Premissa P-6: conversa alheia responde 404 (não 403), para não permitir enumeração.
  Risco crítico: vazamento de conversas entre clientes (IDOR) — LGPD e reputação.

  Contexto:
    Dado que a API de conversas está disponível
    E que "Alice" tem uma conversa aberta

  @CONV-RN01 @R16
  Esquema do Cenário: Sem autenticação válida, "<ação>" é negado (<variação>)
    Quando uma requisição com autenticação "<cabeçalho>" tenta "<ação>" na conversa de "Alice"
    Então a resposta tem status 401 e código de erro "UNAUTHENTICATED"

    Exemplos:
      | variação           | cabeçalho              | ação      |
      | sem cabeçalho      | nenhum                 | criar     |
      | sem cabeçalho      | nenhum                 | encerrar  |
      | token inválido     | Bearer token-invalido  | consultar |
      | esquema Basic      | Basic dXNlcjpwYXNz     | enviar    |

  @CONV-RN08 @R01
  Cenário: Outra pessoa não lê conversa alheia
    Dado que "Alice" enviou a mensagem "Meu código secreto é ALICE-999"
    Quando "Bob" consulta a conversa de "Alice"
    Então a resposta tem status 404 e código de erro "CONVERSATION_NOT_FOUND"
    E a resposta não expõe "ALICE-999"
    E a resposta não expõe "u_alice"

  @CONV-RN08 @R01
  Cenário: Outra pessoa não envia mensagem em conversa alheia
    Quando "Bob" envia a mensagem "injetando" na conversa de "Alice"
    Então a resposta tem status 404 e código de erro "CONVERSATION_NOT_FOUND"
    E o histórico de "Alice" tem 0 mensagens
    E o modelo de linguagem foi chamado 0 vez(es)

  @CONV-RN08 @R01
  Cenário: Outra pessoa não encerra conversa alheia
    Quando "Bob" encerra a conversa de "Alice"
    Então a resposta tem status 404 e código de erro "CONVERSATION_NOT_FOUND"
    E a conversa de "Alice" continua aberta

  @CONV-RN08 @R01
  Cenário: Conversa alheia e inexistente são indistinguíveis
    Quando "Bob" consulta a conversa de "Alice" e uma conversa inexistente
    Então as duas respostas são idênticas em status, código e mensagem

  @CONV-RN08 @R01
  Esquema do Cenário: Identificadores maliciosos não causam erro interno (<caso>)
    Quando "Alice" consulta a conversa "<id>"
    Então a resposta tem status <status>
    E o corpo da resposta contém apenas o objeto de erro

    Exemplos:
      | caso            | id                 | status |
      | path traversal  | ../conversations   | 405    |
      | SQL-like        | conv_' OR '1'='1   | 404    |
      | null byte       | %00                | 404    |
