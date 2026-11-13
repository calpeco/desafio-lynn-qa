# language: pt
# Gerado por test/scripts/qa_scaffold.py a partir de feedback-resposta.md e completado pelo agent-qa-lynn.
# Topo da pirâmide: só o que precisa do navegador (botões, destaque, agradecimento).
# Validação, permissão, logs e contrato ficam em features/api/10_avaliacao_de_respostas_do_agente.feature.
@ui @fdbk
Funcionalidade: Avaliação de respostas do agente (interface)
  Spec: test/specs/feedback-resposta.md
  RN09 — cada resposta do agente mostra 👍/👎; ao avaliar aparece "Obrigado pelo feedback!" e o
  botão escolhido fica destacado. RN04 — avaliar de novo substitui a avaliação anterior.
  O destaque (aria-pressed) é desenhado a partir do histórico relido da API, então também prova
  que a avaliação foi persistida.

  Contexto:
    Dado que a API de conversas está disponível
    E que "Alice" entrou no chat pela interface

  @smoke @FDBK-RN09
  Cenário: Avaliar uma resposta pela interface
    Quando inicia na interface uma nova conversa com o "Agente de suporte"
    E envia na interface a mensagem "Qual o horário de atendimento?"
    E avalia na interface a última resposta do agente com 👍
    Então a interface agradece a avaliação
    E o botão 👍 da última resposta fica destacado
    E a interface fez 1 requisição(ões) de avaliação

  @FDBK-RN09
  Cenário: Cada resposta do agente oferece 👍/👎 e as mensagens da pessoa não
    Quando inicia na interface uma nova conversa com o "Agente de suporte"
    E envia na interface a mensagem "Qual o horário de atendimento?"
    E envia na interface a mensagem "Vocês abrem no sábado?"
    Então a interface mostra 2 mensagem(ns) do usuário e 2 do agente
    E cada resposta do agente mostra os botões 👍 e 👎 e as mensagens do usuário não
    E o texto das respostas do agente não inclui os botões de avaliação

  @FDBK-RN04 @FDBK-RN09 @R02
  Cenário: Trocar a avaliação pela interface substitui a anterior
    Quando inicia na interface uma nova conversa com o "Agente de suporte"
    E envia na interface a mensagem "Qual o horário de atendimento?"
    E avalia na interface a última resposta do agente com 👍
    E avalia na interface a última resposta do agente com 👎
    Então o botão 👎 da última resposta fica destacado
    E a interface agradece a avaliação
    E a interface mostra 1 mensagem(ns) do usuário e 1 do agente
    E a interface fez 2 requisição(ões) de avaliação
