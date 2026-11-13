---
id: XXXX                 # prefixo curto e único (3-6 letras maiúsculas). Vira tag: @XXXX-RN01
titulo: Nome da funcionalidade
area: api                # pasta em test/features/ para os cenários de API (padrão: api)
status: rascunho         # rascunho | pronta  (o agente só gera automação para "pronta")
---

# <Título da funcionalidade>

## Contexto
Para quem é, qual problema resolve e o que está fora de escopo. Duas a cinco linhas.

## Endpoints
<!-- Um por linha: MÉTODO caminho — descrição. Deixe vazio se não houver API. -->
- `POST /api/v1/recurso` — cria ...

## Telas
<!-- Elementos de UI que os testes vão usar. O data-testid é OBRIGATÓRIO (seletor estável). -->
| Elemento | data-testid | Observação |
|---|---|---|
| Botão salvar | `save-button` | desabilitado durante o envio |

## Regras de negócio
<!-- Uma regra por linha, com ID estável. Entre colchetes, opcionalmente:
     camadas sugeridas (unit, api, ui) e riscos da matriz (R01..R16 em docs/ESTRATEGIA_E_RISCOS.md). -->
- **RN01** — Descrição verificável da regra. [camadas: unit, api] [riscos: R09]
- **RN02** — ... [camadas: api, ui] [riscos: R02]

## Critérios de aceite
<!-- Opcional, mas recomendado: cenários em Gherkin (pt), cada um marcado com as regras que cobre.
     O scaffold copia estes blocos para as features e verifica quais passos já existem. -->
```gherkin
@RN01
Cenário: Exemplo de critério de aceite
  Dado que a API de conversas está disponível
  E que "Alice" tem uma conversa aberta
  Quando "Alice" envia a mensagem "oi"
  Então a resposta tem status 201
```

## Dados de teste
Personas disponíveis: `Alice`, `Bob` (autenticadas) e `Visitante` (sem autenticação).
Liste aqui massas específicas, limites e valores de borda.

## Premissas e dúvidas
- **P1** — Premissa adotada enquanto produto não confirma ...
- **D1** — Pergunta em aberto para produto/engenharia ...
