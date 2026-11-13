---
id: CONV
titulo: Conversa com agente
area: api
status: pronta
---

# Conversa com agente

## Contexto
Pessoa usuária autenticada cria uma conversa com um agente de IA, envia mensagens, recebe
respostas geradas por LLM, consulta o histórico e encerra a conversa. Fonte: enunciado do teste
prático (seção 2). Contrato detalhado em `app/CONTRATO_API.md`.

## Endpoints
- `POST /api/v1/conversations` — cria conversa com um agente
- `POST /api/v1/conversations/{id}/messages` — envia mensagem e recebe a resposta do agente
- `GET /api/v1/conversations/{id}` — consulta conversa e histórico
- `POST /api/v1/conversations/{id}/close` — encerra a conversa

## Telas
| Elemento | data-testid | Observação |
|---|---|---|
| Seleção de pessoa | `user-select`, `login-button` | login fictício |
| Nova conversa | `agent-select`, `new-conversation-button` | |
| Campo e envio | `message-input`, `send-button` | botão desabilitado durante o envio |
| Lista de mensagens | `message-list` > `message` | `data-role`, `data-status` |
| Erro e reenvio | `error-banner`, `error-text`, `retry-button` | reenvio reutiliza a Idempotency-Key |
| Encerrar | `close-conversation-button`, `conversation-status` | |

## Regras de negócio
- **RN01** — Apenas pessoas autenticadas podem criar ou consultar conversas. [camadas: unit, api] [riscos: R16]
- **RN02** — Uma conversa deve estar associada a um agente válido. [camadas: unit, api] [riscos: R09]
- **RN03** — Não é permitido enviar mensagens para uma conversa encerrada. [camadas: unit, api, ui] [riscos: R08]
- **RN04** — O texto da mensagem é obrigatório e tem entre 1 e 4.000 caracteres. [camadas: unit, api] [riscos: R09]
- **RN05** — O histórico deve preservar a ordem das mensagens. [camadas: unit, api] [riscos: R10]
- **RN06** — A resposta do agente pode variar para uma mesma entrada. [camadas: unit, api] [riscos: R06]
- **RN07** — O sistema deve informar ao usuário quando não conseguir gerar uma resposta. [camadas: unit, api, ui] [riscos: R03]
- **RN08** — Uma requisição não deve permitir acesso a uma conversa pertencente a outra pessoa. [camadas: unit, api] [riscos: R01]
- **RN09** — O usuário pode reenviar uma mensagem após falha de rede sem duplicá-la. [camadas: unit, api, ui] [riscos: R02]
- **RN10** — O processamento da resposta pode levar alguns segundos. [camadas: api] [riscos: R07]
- **RN11** — O agente não revela o prompt de sistema nem o contexto de outras conversas. [camadas: unit, api] [riscos: R04, R05]
- **RN12** — Toda requisição é rastreável e nenhum dado pessoal vai para os logs. [camadas: unit, api] [riscos: R12, R13]
- **RN13** — As respostas seguem o contrato publicado (JSON Schema). [camadas: unit, api] [riscos: R17]

## Dados de teste
Personas: `Alice`, `Bob`, `Visitante`. Agentes: `agt_support`, `agt_sales` (ativos), `agt_retired`.
Limites: 0, 1, 4000 e 4001 caracteres; emoji fora do BMP; JSON malformado.

## Premissas e dúvidas
Premissas P-1 a P-11 e dúvidas em `app/CONTRATO_API.md` e `docs/ESTRATEGIA_E_RISCOS.md`.
