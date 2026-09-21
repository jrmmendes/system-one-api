# System One API — Usage Guide

API REST que expõe o modelo **Laya** (System 1, não-autoregressivo) para classificação probabilística em tempo real. Retorna respostas estruturadas em milissegundos, sem parsing de JSON gerado por LLMs tradicionais.

## Setup

```bash
docker compose up --build
```

O modelo será baixado do HuggingFace na primeira execução (~400MB) e cacheado localmente.

**Variáveis de ambiente:**

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `LAYA_DEVICE` | `cpu` | Device de inferência: `cpu` ou `cuda` |

**Docs interativos:** `http://localhost:8000/docs`

---

## Endpoint

### `POST /classify`

Envia texto + perguntas tipadas e recebe classificações probabilísticas em single-pass.

**Content-Type:** `application/json`

---

## Request Schema

```json
{
  "text": "string (1-10000 chars)",
  "questions": {
    "<question_id>": { "<question_definition>" }
  }
}
```

### Tipos de perguntas

#### `choice` — Categorização fechada

Classifica o texto em uma das opções fornecidas.

```json
{
  "type": "choice",
  "options": ["option_a", "option_b", "option_c"]
}
```

`options` aceita dois formatos:

- **Array de strings:** lista simples de categorias
- **Dict com descrições:** para opções que precisam de contexto adicional

```json
{
  "type": "choice",
  "options": {
    "suporte_tecnico": "Problemas técnicos, bugs, erros",
    "financeiro": "Cobranças, faturas, pagamentos",
    "comercial": "Vendas, upgrades, novos planos"
  }
}
```

#### `noul` — Binário Sim/Não probabilístico

Avalia se uma afirmação é verdadeira ou falsa para o texto dado.

```json
{
  "type": "noul",
  "instruction": "Descrição da afirmação a ser avaliada.",
  "true_criteria": "Descrição opcional do que configura TRUE",
  "false_criteria": "Descrição opcional do que configura FALSE"
}
```

- `true_criteria` e `false_criteria` são opcionais e servem para calibrar o modelo

#### `score` — Régua numérica

Avalia o texto em uma escala contínua com níveis nomeados.

```json
{
  "type": "score",
  "instruction": "Descrição do critério a ser avaliado.",
  "levels": ["nível 0", "nível 1", "nível 2", "nível 3", "nível 4"]
}
```

- `levels` é opcional; define rótulos para cada posição da escala (0 a N)

---

## Response Schema

```json
{
  "model": "laya-rl-agent",
  "answers": {
    "<question_id>": { ... }
  },
  "usage": {
    "input_tokens": 176,
    "output_tokens": 0
  },
  "routing": {
    "model": "english",
    "repo": "convaiinnovations/laya",
    "reason": "English Latin text",
    "detection": {
      "script": "latin",
      "script_profile": { "latin": 1.0 },
      "language": null,
      "is_english": true,
      "non_latin_fraction": 0.0
    }
  }
}
```

### Interpretação dos answers por tipo

#### Resposta `choice`

```json
{
  "type": "choice",
  "choice": "suporte_tecnico",
  "probabilities": {
    "suporte_tecnico": 0.7369,
    "financeiro": 0.1015,
    "comercial": 0.0780,
    "outro": 0.0836
  },
  "confidence": 0.3771,
  "action": { "act_probability": 1.0 }
}
```

- **`choice`**: opção vencedora
- **`probabilities`**: distribuição de probabilidade sobre todas as opções
- **`confidence`**: margem de confiança (distância entre a 1ª e 2ª opção). Quanto maior, mais decisiva a classificação
- **Decisão recomendada:** usar `choice` diretamente; inspecionar `probabilities` apenas se `confidence < 0.2` (empate técnico)

#### Resposta `noul`

```json
{
  "type": "noul",
  "noul": 0.8719,
  "confidence": 0.8719,
  "action": { "act_probability": 1.0 }
}
```

- **`noul`**: probabilidade de **TRUE** (0.0 = definitivamente não, 1.0 = definitivamente sim)
- **`confidence`**: quão certo o modelo está dessa avaliação
- **Decisão recomendada:** `noul >= 0.7` → TRUE, `noul <= 0.3` → FALSE, entre 0.3–0.7 → incerto (requer fallback)

#### Resposta `score`

```json
{
  "type": "score",
  "score": 2.0341,
  "legend": {
    "0": "baixo",
    "1": "medio",
    "2": "alto",
    "3": "critico",
    "4": "bloqueante"
  },
  "probabilities": {
    "0": 0.0962,
    "1": 0.2984,
    "2": 0.2413,
    "3": 0.2035,
    "4": 0.1607
  },
  "confidence": 0.0389,
  "action": { "act_probability": 1.0 }
}
```

- **`score`**: valor contínuo na escala (pode ser fracionário)
- **`legend`**: mapeamento de índice → rótulo (quando `levels` foi fornecido)
- **`probabilities`**: distribuição sobre cada nível
- **`confidence`**: concentração da distribuição. Valores baixos indicam dispersão (modelo indeciso)
- **Decisão recomendada:** usar `Math.round(score)` para mapear ao nível mais próximo, ou usar `probabilities` para lógica fuzzy

### Interpretação do `routing`

O campo `routing` indica qual checkpoint foi usado e por quê:

- **`reason: "no letters detected"`** → input sem letras, modelo caiu no fallback (pode ser impreciso)
- **`reason: "English Latin text"`** → detecção normal
- **`detection.is_english`**: se `false`, o modelo usou checkpoint específico do idioma detectado

**Atenção:** inputs puramente numéricos ou com muitos símbolos produzem `script: "unknown"` e resultados não-confiáveis.

---

## Exemplos de uso

### Tool routing (escolha entre read, write ou bash)

```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{
  "text": "I need to read the contents of config.yaml to check the environment variables.",
  "questions": {
    "tool": {
      "type": "choice",
      "options": ["read", "write", "bash"]
    },
    "high_confidence": {
      "type": "noul",
      "instruction": "Does the user describe a clear and unambiguous action that allows identifying the correct tool with high confidence?"
    },
    "complexity": {
      "type": "score",
      "instruction": "Rate the technical complexity of the described task from 1 (trivial) to 5 (highly complex).",
      "levels": ["trivial", "simple", "moderate", "complex", "highly complex"]
    },
    "involves_sensitive_data": {
      "type": "noul",
      "instruction": "Does the task involve reading or manipulating sensitive data such as credentials, tokens, or secrets?"
    }
  }
}'
```

### Triagem de suporte

```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{
  "text": "My production database is down and all users are affected. We need immediate help.",
  "questions": {
    "category": {
      "type": "choice",
      "options": {
        "technical_support": "Technical issues, bugs, system errors",
        "billing": "Invoices, charges, payments",
        "sales": "Upgrades, new plans, demos"
      }
    },
    "churn_risk": {
      "type": "noul",
      "instruction": "Does the user express clear intent to cancel or abandon the product?",
      "true_criteria": "User explicitly mentions cancellation, leaving, or switching to competitor",
      "false_criteria": "User is frustrated but still engaged with the product"
    },
    "severity": {
      "type": "score",
      "instruction": "Rate the criticality of the reported issue from 1 (low) to 5 (blocking).",
      "levels": ["low", "minor", "moderate", "high", "blocking"]
    },
    "escalation_needed": {
      "type": "noul",
      "instruction": "Does the situation require immediate escalation to a senior engineer or manager?"
    }
  }
}'
```

---

## Constraints e limitações

| Restrição | Detalhe |
|-----------|---------|
| **Tamanho do texto** | 1 a 10.000 caracteres. Textos maiores são truncados pelo `clean_email_body` |
| **Idioma** | Detecção automática. Checkpoints disponíveis: english, português, espanhol, francês, italiano, alemão |
| **Inputs numéricos puros** | Não use o Laya para cálculos ou validação de expressões matemáticas. Faça isso em código |
| **Validação de regras de negócio** | Lógica determinística (datas, permissões, thresholds fixos) deve ser feita antes/depois do Laya |
| **Latência cold start** | ~30s na primeira execução (download do modelo). Depois: <50ms por request em CPU |
| **Sanitização automática** | O texto é higienizado via `clean_email_body` (remove assinaturas, disclaimers, HTML) antes da inferência |

---

## Estrutura do projeto

```
system-one-api/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app + lifespan (model loading)
│   ├── models.py                # Pydantic schemas (request/response)
│   ├── routes/
│   │   └── classify.py          # POST /classify handler
│   └── services/
│       └── laya_service.py      # Singleton wrapper around laya.Router
├── main.py                      # Dev entrypoint (uvicorn with reload)
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

### Padrões importantes

- **Singleton:** `LayaService` é instanciado uma única vez no `lifespan` do FastAPI com `preload=True`. Nunca reinstanciar dentro de uma request (latência salta de ~30ms para >7s)
- **Sanitização:** todo texto passa por `clean_email_body` antes do `predict()` para remover ruído
- **Tradução de schema:** o service traduz a API pública (`options`, `instruction`, `levels`) para o formato interno do Laya (`criteria`, `instructions`)
