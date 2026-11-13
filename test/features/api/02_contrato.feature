# language: pt
@api @contract
Funcionalidade: Contrato das respostas
  Risco: quebra de contrato silenciosa quebra frontend, SDKs e integrações.
  Os contratos são JSON Schema (draft 2020-12) em contracts/.

  Contexto:
    Dado que a API de conversas está disponível
    E que "Alice" tem uma conversa aberta

  @CONV-RN13 @R17
  Cenário: Consultar e encerrar seguem o contrato de conversa
    Quando "Alice" consulta a conversa
    Então a resposta segue o contrato "conversation"
    Quando "Alice" encerra a conversa
    Então a resposta segue o contrato "conversation"

  @CONV-RN13 @R17
  Cenário: Resposta do agente traz metadados de custo e latência
    Quando "Alice" envia a mensagem "Olá"
    Então a resposta segue o contrato "send_message_response"
    E a resposta do agente informa tokens de prompt e de resposta maiores que zero
    E a mensagem do usuário não tem metadados

  @CONV-RN13 @R17
  Cenário: Sucesso e erro usam Content-Type JSON
    Quando "Alice" consulta a conversa
    Então a resposta tem Content-Type JSON
    Quando "Visitante" consulta a conversa de "Alice"
    Então a resposta tem Content-Type JSON

  @CONV-RN13 @R17
  Cenário: Rota inexistente responde com o envelope de erro padrão
    Quando "Alice" chama "GET" em "/api/v1/nao-existe"
    Então a resposta tem status 404 e código de erro "NOT_FOUND"
