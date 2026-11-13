# language: pt
@api @functional
Funcionalidade: Ciclo de vida da conversa e ordem do histórico
  Regras de negócio — não é permitido enviar mensagem para conversa encerrada; o histórico preserva a ordem.

  Contexto:
    Dado que a API de conversas está disponível
    E que "Alice" tem uma conversa aberta

  @CONV-RN03 @R08
  Cenário: Mensagem em conversa encerrada é recusada sem gastar tokens
    Dado que "Alice" enviou a mensagem "primeira"
    E que "Alice" encerrou a conversa
    Quando "Alice" envia a mensagem "depois de encerrar"
    Então a resposta tem status 409 e código de erro "CONVERSATION_CLOSED"
    E a mensagem de erro para o usuário contém "encerrada"
    E o histórico de "Alice" tem 2 mensagens
    E o modelo de linguagem foi chamado 1 vez(es)

  @CONV-RN03 @R08
  Cenário: Encerrar duas vezes é idempotente (premissa P-10)
    Dado que "Alice" encerrou a conversa
    Quando "Alice" encerra a conversa
    Então a resposta tem status 200
    E a data de encerramento não mudou

  @CONV-RN05 @R10
  Cenário: Histórico preserva a ordem em envios sequenciais
    Quando "Alice" envia 5 mensagens em sequência
    Então o histórico tem seq contíguo de 1 a 10
    E as mensagens do usuário estão na ordem em que foram enviadas
    E cada resposta do agente vem logo após a sua pergunta

  @CONV-RN05 @R10
  Cenário: Histórico consistente sob envios simultâneos (ex.: duas abas)
    Quando "Alice" envia 8 mensagens simultâneas
    Então todos os envios simultâneos tiveram status 201
    E o histórico tem seq contíguo de 1 a 16
    E cada resposta do agente vem logo após a sua pergunta

  @CONV-RN03 @R08
  Cenário: Mensagem na fila é recusada se a conversa for encerrada (corrida com o close)
    Dado que o modelo de linguagem responde em 600 ms com timeout de 5000 ms
    Quando "Alice" envia em segundo plano a mensagem "A"
    E "Alice" envia em segundo plano a mensagem "B"
    E "Alice" encerra a conversa
    Então o envio em segundo plano de "A" terminou com status 201
    E o envio em segundo plano de "B" terminou com status 409 e código de erro "CONVERSATION_CLOSED"
    E as mensagens do usuário no histórico são apenas "A"
