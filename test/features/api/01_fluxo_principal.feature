# language: pt
@api @smoke @functional
Funcionalidade: Conversa com agente — fluxo principal
  Como pessoa usuária autenticada
  Quero conversar com um agente de IA
  Para tirar dúvidas e manter o histórico da conversa

  Risco: fluxo principal quebrado bloqueia o lançamento.

  Contexto:
    Dado que a API de conversas está disponível

  @CONV-RN05 @CONV-RN13
  Cenário: Criar, conversar, consultar o histórico e encerrar
    Quando "Alice" cria uma conversa com o agente "agt_support"
    Então a resposta tem status 201
    E a resposta segue o contrato "conversation"
    E a conversa está aberta, sem mensagens e pertence a "u_alice"
    Quando "Alice" envia a mensagem "Qual o horário de atendimento?"
    Então a resposta tem status 201
    E a resposta segue o contrato "send_message_response"
    E a resposta do agente referencia a mensagem enviada
    Quando "Alice" consulta a conversa
    Então a resposta segue o contrato "conversation"
    E o histórico contém, em ordem:
      | papel     | conteúdo                       | status    |
      | user      | Qual o horário de atendimento? | completed |
      | assistant | *                              | completed |
    Quando "Alice" encerra a conversa
    Então a resposta tem status 200
    E a resposta segue o contrato "conversation"
    E a conversa está encerrada
    E o histórico de "Alice" tem 2 mensagens

  @CONV-RN05
  Cenário: O agente usa o contexto da própria conversa entre turnos
    Dado que "Alice" tem uma conversa aberta
    Quando "Alice" envia a mensagem "Meu código secreto é ZEBRA-42"
    E "Alice" envia a mensagem "Qual é o meu código secreto?"
    Então o agente respondeu contendo "ZEBRA-42"
