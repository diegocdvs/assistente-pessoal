# ADR-005 — LLMProvider desacoplado

Status: aceito

## Contexto

O projeto deve usar IA para refinar classificação, gerar resumos e propor ações, mas não pode ficar preso a um SDK ou provedor específico.

## Decisão

Toda chamada de IA deve passar por uma interface `LLMProvider`.

Implementações futuras podem incluir:

- OpenAIProvider;
- GeminiProvider;
- ClaudeProvider;
- LocalProvider.

O domínio não deve importar SDKs de provedores diretamente.

## Consequências

- Trocar modelo vira configuração/adaptação isolada.
- Testes podem usar provider fake.
- Custos e limites podem ser medidos por camada.

## Alternativas descartadas

- Chamar OpenAI/Gemini diretamente no Classifier.
- Embutir prompts dentro do DailyJob.
- IA executar ações externas.
