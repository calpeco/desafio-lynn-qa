# language: pt
@ui
Funcionalidade: Chat com o agente pela interface (E2E)
  Topo da pirâmide: poucos cenários, só o que precisa do navegador para ser verificado.
  O foco são os comportamentos que a API sozinha não garante: o duplo clique e o reenvio
  após falha de rede da Parte C, o feedback de erro ao usuário e o bloqueio de conversa
  encerrada.

  Contexto:
    Dado que a API de conversas está disponível
    E que "Alice" entrou no chat pela interface

  @smoke @CONV-RN06
  Cenário: Conversar com o agente pela interface
    Quando inicia na interface uma nova conversa com o "Agente de suporte"
    E envia na interface a mensagem "Qual o horário de atendimento?"
    Então a interface mostra 1 mensagem(ns) do usuário e 1 do agente
    E a última mensagem na interface é do agente e contém "18h"
    E o campo de mensagem está vazio

  @smoke @CONV-RN09 @R02
  Cenário: Duplo clique em Enviar gera uma única mensagem (Parte C)
    Dado que o modelo de linguagem responde em 600 ms com timeout de 5000 ms
    Quando inicia na interface uma nova conversa com o "Agente de suporte"
    E digita na interface "clique duplo" e clica duas vezes em Enviar
    Então a interface mostra 1 mensagem(ns) do usuário e 1 do agente
    E a interface fez 1 requisição(ões) de envio de mensagem
    E o modelo de linguagem foi chamado 1 vez(es)

  @CONV-RN09 @R02
  Cenário: Falha de rede depois do servidor processar: o reenvio não duplica (Parte C)
    Dado que a próxima resposta de envio de mensagem será perdida na rede
    Quando inicia na interface uma nova conversa com o "Agente de suporte"
    E envia na interface a mensagem "minha pergunta"
    Então a interface exibe o erro "Falha de conexão"
    E a interface oferece "Tentar novamente"
    Quando clica em "Tentar novamente" na interface
    Então a interface mostra 1 mensagem(ns) do usuário e 1 do agente
    E a interface não exibe erro
    E o modelo de linguagem foi chamado 1 vez(es)

  @CONV-RN07 @CONV-RN09 @R03
  Cenário: Agente indisponível: a pessoa é informada e consegue reenviar sem duplicar
    Dado que o modelo de linguagem está no modo "error"
    Quando inicia na interface uma nova conversa com o "Agente de suporte"
    E envia na interface a mensagem "preciso de ajuda"
    Então a interface exibe o erro "Não foi possível gerar uma resposta"
    E a interface oferece "Tentar novamente"
    E a interface mostra 1 mensagem(ns) do usuário e 0 do agente
    Quando o modelo de linguagem volta a funcionar
    E clica em "Tentar novamente" na interface
    Então a interface mostra 1 mensagem(ns) do usuário e 1 do agente
    E a interface não exibe erro

  @CONV-RN03 @R08
  Cenário: Conversa encerrada bloqueia novos envios na interface
    Quando inicia na interface uma nova conversa com o "Agente de suporte"
    E envia na interface a mensagem "oi"
    E encerra a conversa na interface
    Então a interface informa "Conversa encerrada."
    E o campo de mensagem e o botão Enviar estão desabilitados

  @security @R18
  Cenário: Conteúdo com HTML é exibido como texto, sem executar script
    Quando inicia na interface uma nova conversa com o "Agente de suporte"
    E envia na interface a mensagem "<img src=x onerror=alert(1)>"
    Então a primeira mensagem do usuário aparece como o texto literal "<img src=x onerror=alert(1)>"
    E nenhum diálogo JavaScript foi aberto
