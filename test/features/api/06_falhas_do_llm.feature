# language: pt
@api @resilience @llm
Funcionalidade: Falha, indisponibilidade e lentidão do modelo de linguagem
  Regra de negócio — o sistema deve informar a pessoa usuária quando não conseguir gerar uma resposta.
  Premissas P-7/P-8: a mensagem do usuário fica salva como "failed"; erro 503/504 com
  mensagem clara e Retry-After. O timeout é imposto pela aplicação, não pelo provedor.

  Contexto:
    Dado que a API de conversas está disponível
    E que "Alice" tem uma conversa aberta

  @CONV-RN07 @R03
  Esquema do Cenário: Usuário é informado quando não há resposta (<falha>)
    Dado que o modelo de linguagem está no modo "<modo>" com atraso de 1500 ms e timeout de 300 ms
    Quando "Alice" envia a mensagem "Olá, preciso de ajuda"
    Então a resposta tem status <status> e código de erro "<código>"
    E a mensagem de erro para o usuário contém "não foi possível gerar uma resposta"
    E a resposta orienta tentar novamente depois
    E o histórico contém, em ordem:
      | papel | conteúdo              | status |
      | user  | Olá, preciso de ajuda | failed |

    Exemplos:
      | falha          | modo    | status | código          |
      | indisponível   | error   | 503    | LLM_UNAVAILABLE |
      | timeout        | timeout | 504    | LLM_TIMEOUT     |

  @CONV-RN10 @R07
  Cenário: O servidor corta no timeout em vez de esperar o provedor
    Dado que o modelo de linguagem está no modo "timeout" com atraso de 5000 ms e timeout de 500 ms
    Quando "Alice" envia a mensagem "oi"
    Então a resposta tem status 504
    E a resposta chegou em menos de 2000 ms

  @CONV-RN10 @R07
  Cenário: Resposta lenta dentro do orçamento é entregue com a latência real
    Dado que o modelo de linguagem responde em 800 ms com timeout de 3000 ms
    Quando "Alice" envia a mensagem "oi"
    Então a resposta tem status 201
    E a latência reportada pelo agente é de pelo menos 770 ms

  @CONV-RN07 @R03
  Cenário: O serviço se recupera após indisponibilidade
    Dado que o modelo de linguagem está no modo "error"
    E que "Alice" enviou a mensagem "tentativa 1"
    Quando o modelo de linguagem volta a funcionar
    E "Alice" envia a mensagem "tentativa 2"
    Então a resposta tem status 201
    E a resposta segue o contrato "send_message_response"

  @CONV-RN05 @CONV-RN07 @R03
  Cenário: Falha não corrompe o histórico existente
    Dado que "Alice" enviou a mensagem "antes da falha"
    E que o modelo de linguagem está no modo "error"
    E que "Alice" enviou a mensagem "durante a falha"
    Quando o modelo de linguagem volta a funcionar
    E "Alice" envia a mensagem "depois da falha"
    Então o histórico contém, em ordem:
      | papel     | conteúdo        | status    |
      | user      | antes da falha  | completed |
      | assistant | *               | completed |
      | user      | durante a falha | failed    |
      | user      | depois da falha | completed |
      | assistant | *               | completed |
    E o histórico tem seq contíguo de 1 a 5
