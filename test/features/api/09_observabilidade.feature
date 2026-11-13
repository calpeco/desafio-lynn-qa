# language: pt
@api @observability
Funcionalidade: Observabilidade e proteção de dados nos logs
  Risco: incidentes impossíveis de investigar (sem correlação) e dados pessoais vazando para logs.

  Contexto:
    Dado que a API de conversas está disponível
    E que "Alice" tem uma conversa aberta

  @CONV-RN12 @R13
  Cenário: O identificador da requisição é propagado
    Quando "Alice" envia a mensagem "oi" com o identificador de requisição "qa-trace-123"
    Então a resposta tem o cabeçalho "X-Request-ID" igual a "qa-trace-123"

  @CONV-RN12 @R13
  Cenário: Um identificador é gerado quando o cliente não envia
    Quando "Visitante" consulta a conversa "x" sem identificador de requisição
    Então a resposta tem o cabeçalho "X-Request-ID" preenchido

  @CONV-RN12 @R13
  Cenário: Logs estruturados permitem rastrear a requisição de ponta a ponta
    Quando "Alice" envia a mensagem "oi" com o identificador de requisição "qa-trace-456"
    Então os logs da requisição "qa-trace-456" contêm os eventos "message.received;message.answered;http.access"
    E o evento de log "message.answered" contém os campos "latency_ms;prompt_tokens;completion_tokens;finish_reason"

  @CONV-RN12 @R13
  Cenário: Falha do LLM fica registrada com o tipo
    Dado que o modelo de linguagem está no modo "error"
    Quando "Alice" envia a mensagem "oi" com o identificador de requisição "qa-trace-789"
    Então o evento de log "llm.failure" da requisição "qa-trace-789" tem "kind" igual a "unavailable"

  @CONV-RN12 @R12
  Cenário: Conteúdo da mensagem e credenciais não vão para os logs
    Quando "Alice" envia a mensagem "Meu CPF é 123.456.789-00 e meu cartão 4111 1111 1111 1111"
    Então os logs não contêm "123.456.789-00;4111 1111;Bearer;token-alice"
