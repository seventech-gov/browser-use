# SevenTech - Guia Completo

Plataforma de automação browser com IA. Mapeia objetivos uma vez (com LLM), executa infinitas vezes (sem LLM).

---

## 🚀 Setup Rápido

### 1. Instalar

```bash
# Já está pronto! Apenas ative o ambiente
source .venv/bin/activate
```

### 2. Configurar

```bash
# Copiar .env
cp seventech/.env.example seventech/.env

# Editar e adicionar sua API key
nano seventech/.env
```

Adicione:
```
GEMINI_API_KEY=sua_chave_aqui
```

Obter chave grátis: https://aistudio.google.com/app/apikey

### 3. Rodar

```bash
uv run uvicorn seventech.api.server:app --reload --host 0.0.0.0 --port 8000
```

Acesse: **http://localhost:8000**

---

## 📡 Endpoints da API

Base URL: `http://localhost:8000/api/v1`

### 🗺️ Mapeamento Interativo

#### 1. Iniciar Sessão de Mapeamento

```bash
POST /mapping/start
```

**Body:**
```json
{
  "objective": "Ir para site X e fazer Y",
  "starting_url": "https://example.com",  // opcional
  "tags": ["tag1", "tag2"],                // opcional
  "plan_name": "nome_do_plano"             // opcional
}
```

**Response:**
```json
{
  "session_id": "01abc123...",
  "status": "started",
  "sse_url": "/api/v1/mapping/sessions/01abc123.../events",
  "status_url": "/api/v1/mapping/sessions/01abc123..."
}
```

**Exemplo:**
```bash
curl -X POST http://localhost:8000/api/v1/mapping/start \
  -H "Content-Type: application/json" \
  -d '{
    "objective": "Consultar IPTU no site da prefeitura",
    "tags": ["iptu"]
  }'
```

---

#### 2. Consultar Status da Sessão

```bash
GET /mapping/sessions/{session_id}
```

**Response:**
```json
{
  "session_id": "01abc123...",
  "objective": "Consultar IPTU...",
  "status": "running",  // ou "waiting_for_input", "completed", "failed"
  "steps_completed": 5,
  "collected_parameters": [
    {
      "name": "inscricao_imobiliaria",
      "label": "Inscrição Imobiliária",
      "value": "1234567890"
    }
  ],
  "current_input_request": {
    "field_name": "cpf",
    "field_label": "CPF",
    "prompt": "Digite seu CPF",
    "placeholder": "123.456.789-00"
  }
}
```

---

#### 3. Fornecer Input (quando necessário)

```bash
POST /mapping/sessions/{session_id}/input
```

**Body:**
```json
{
  "value": "1234567890"
}
```

**Quando usar:** Quando `status` = `"waiting_for_input"`

**Exemplo:**
```bash
curl -X POST http://localhost:8000/api/v1/mapping/sessions/01abc.../input \
  -H "Content-Type: application/json" \
  -d '{"value": "1234567890"}'
```

---

#### 4. Criar Plano da Sessão

```bash
POST /mapping/sessions/{session_id}/create-plan
```

**Quando usar:** Quando `status` = `"completed"`

**Response:**
```json
{
  "metadata": {
    "plan_id": "01xyz789...",
    "name": "consulta_iptu",
    "required_params": ["inscricao_imobiliaria"]
  },
  "steps": [...]
}
```

---

### 📋 Gerenciar Planos

#### Listar Planos

```bash
GET /plans
GET /plans?tags=iptu,consulta  # filtrar por tags
```

#### Buscar Planos

```bash
GET /plans/search?query=iptu
```

#### Obter Plano Específico

```bash
GET /plans/{plan_id}
```

#### Deletar Plano

```bash
DELETE /plans/{plan_id}
```

---

### ⚡ Executar Planos (MONETIZAÇÃO)

#### Executar Plano

```bash
POST /execute/{plan_id}
```

**Body:**
```json
{
  "inscricao_imobiliaria": "1234567890",
  "cpf": "123.456.789-00",
  "qualquer_parametro": "valor"
}
```

**Response:**
```json
{
  "execution_id": "01exec123...",
  "plan_id": "01xyz789...",
  "status": "success",
  "artifacts": [
    {
      "type": "screenshot",
      "name": "resultado.png",
      "content": "base64_encoded_data"
    }
  ],
  "steps_completed": 10,
  "total_steps": 10,
  "execution_time_ms": 8500
}
```

**🔥 Este é o endpoint principal para monetizar!**

- Sem LLM (rápido e barato)
- Determinístico (sempre funciona igual)
- Ilimitado (execute 1000x se quiser)

**Exemplo:**
```bash
curl -X POST http://localhost:8000/api/v1/execute/01xyz789... \
  -H "Content-Type: application/json" \
  -d '{"inscricao_imobiliaria": "1234567890"}'
```

---

#### Listar Execuções

```bash
GET /executions
GET /executions?plan_id=01xyz789...  # filtrar por plano
```

#### Obter Execução Específica

```bash
GET /executions/{execution_id}
```

---

## 🔄 Fluxo Completo

### 1. Mapear Objetivo (uma vez)

```bash
# Iniciar
SESSION_ID=$(curl -X POST http://localhost:8000/api/v1/mapping/start \
  -H "Content-Type: application/json" \
  -d '{"objective": "Consultar IPTU no site X"}' \
  | jq -r '.session_id')

# Monitorar status
watch -n 2 "curl -s http://localhost:8000/api/v1/mapping/sessions/$SESSION_ID | jq '.status'"
```

### 2. Fornecer Input (se necessário)

```bash
# Quando status = "waiting_for_input"
curl -X POST http://localhost:8000/api/v1/mapping/sessions/$SESSION_ID/input \
  -H "Content-Type: application/json" \
  -d '{"value": "1234567890"}'
```

### 3. Criar Plano (quando completo)

```bash
# Quando status = "completed"
PLAN_ID=$(curl -X POST http://localhost:8000/api/v1/mapping/sessions/$SESSION_ID/create-plan \
  | jq -r '.metadata.plan_id')

echo "Plan ID: $PLAN_ID"
```

### 4. Executar Plano (infinitas vezes)

```bash
# Primeira execução
curl -X POST http://localhost:8000/api/v1/execute/$PLAN_ID \
  -H "Content-Type: application/json" \
  -d '{"inscricao_imobiliaria": "1111111"}'

# Segunda execução (mesma API, novos parâmetros)
curl -X POST http://localhost:8000/api/v1/execute/$PLAN_ID \
  -H "Content-Type: application/json" \
  -d '{"inscricao_imobiliaria": "2222222"}'

# Terceira, quarta, milésima... sem LLM!
```

---

## 💻 Exemplos em Python

### Cliente HTTP Completo

```python
import asyncio
import httpx

async def workflow():
    async with httpx.AsyncClient(timeout=300) as client:
        # 1. Iniciar mapeamento
        resp = await client.post('http://localhost:8000/api/v1/mapping/start', json={
            'objective': 'Consultar IPTU',
            'tags': ['iptu']
        })
        session_id = resp.json()['session_id']
        print(f"Session: {session_id}")

        # 2. Monitorar status
        while True:
            await asyncio.sleep(3)
            resp = await client.get(f'http://localhost:8000/api/v1/mapping/sessions/{session_id}')
            state = resp.json()

            print(f"Status: {state['status']}")

            # 3. Fornecer input se necessário
            if state['status'] == 'waiting_for_input':
                req = state['current_input_request']
                print(f"Input needed: {req['prompt']}")
                value = input(f"{req['field_label']}: ")

                await client.post(
                    f'http://localhost:8000/api/v1/mapping/sessions/{session_id}/input',
                    json={'value': value}
                )

            # 4. Criar plano quando completo
            elif state['status'] == 'completed':
                resp = await client.post(
                    f'http://localhost:8000/api/v1/mapping/sessions/{session_id}/create-plan'
                )
                plan = resp.json()
                plan_id = plan['metadata']['plan_id']
                print(f"Plan ID: {plan_id}")
                break

        # 5. Executar plano
        params = {param: input(f"Enter {param}: ")
                  for param in plan['metadata']['required_params']}

        resp = await client.post(
            f'http://localhost:8000/api/v1/execute/{plan_id}',
            json=params
        )
        result = resp.json()
        print(f"Execution: {result['status']} in {result['execution_time_ms']}ms")

asyncio.run(workflow())
```

### Executar Script Exemplo

```bash
uv run python seventech/examples/05_api_client_complete.py
```

---

## 💰 Monetização

### Modelo de Preço

```python
PRICING = {
    'mapping': 5.00,      # Por sessão (uma vez)
    'execution': 0.10,    # Por execução (ilimitado)
}
```

### Exemplo de Receita

**1 cliente cria 1 plano e executa 100x/mês:**

```
Mapeamento:    1 × $5.00  = $5.00
Execuções:   100 × $0.10  = $10.00
─────────────────────────────────────
Total/mês:                  $15.00

Seus custos:
- LLM (mapping): ~$0.50
- Execuções:     ~$0.10
─────────────────────────────────────
Custo total:     ~$0.60

LUCRO: $14.40/cliente/mês (96% margem)
```

**1000 clientes:**

```
Receita: $15,000/mês
Custos:     $600/mês
──────────────────────
Lucro:  $14,400/mês 🚀
```

---

## 🔐 Adicionar Autenticação (Produção)

Editar `seventech/api/server.py`:

```python
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name='X-API-Key')

async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    # Verificar no banco de dados
    if api_key not in valid_api_keys:
        raise HTTPException(403, 'Invalid API key')
    return api_key

# Adicionar em cada endpoint
@app.post('/api/v1/execute/{plan_id}')
async def execute_plan(
    plan_id: str,
    params: dict,
    api_key: str = Depends(verify_api_key)  # ← Adicionar
):
    # ... resto do código
```

**Uso:**
```bash
curl -X POST http://localhost:8000/api/v1/execute/123 \
  -H "X-API-Key: seu_api_key_aqui" \
  -H "Content-Type: application/json" \
  -d '{"param": "value"}'
```

---

## 🐳 Deploy com Docker

### Dockerfile

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y chromium && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY seventech/requirements.txt .
RUN pip install -r requirements.txt

COPY seventech/ ./seventech/

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "seventech.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    restart: unless-stopped
```

**Deploy:**
```bash
docker-compose up -d
```

---

## 🆘 Troubleshooting

### "Module not found"
```bash
source .venv/bin/activate
```

### "API key not found"
```bash
# Editar .env
nano seventech/.env
# Adicionar: GEMINI_API_KEY=sua_chave
```

### "Port 8000 already in use"
```bash
# Matar processo
lsof -ti:8000 | xargs kill -9

# Ou usar outra porta
uv run uvicorn seventech.api.server:app --port 8001
```

### Sessão não completa
- Verificar logs do servidor
- Timeout muito curto? Aumentar em `.env`
- LLM travado? Verificar API key válida

---

## 📂 Estrutura do Projeto

```
seventech/
├── api/
│   ├── server.py              # API REST
│   └── session_manager.py     # Gerenciamento de sessões
├── mapper/
│   ├── interactive.py         # Mapeamento interativo
│   ├── session.py             # Sessões
│   └── collector.py           # Coleta de parâmetros
├── planner/
│   └── service.py             # Criação de planos
├── executor/
│   └── service.py             # Execução (SEM LLM)
├── storage/
│   └── service.py             # Persistência
├── examples/
│   └── 05_api_client_complete.py  # Cliente exemplo
└── GUIDE.md                   # Este arquivo
```

---

## 🎯 Próximos Passos

1. **Testar localmente** (hoje)
   ```bash
   uv run uvicorn seventech.api.server:app --reload
   ```

2. **Criar 2-3 planos** (esta semana)
   - Testar mapeamento interativo
   - Executar planos múltiplas vezes

3. **Deploy beta** (próxima semana)
   - Docker
   - SSL com Cloudflare
   - 10 clientes beta

4. **Adicionar autenticação** (semana 2)
   - API keys
   - Rate limiting
   - Billing

5. **Monetizar** (mês 1+)
   - Portal do cliente
   - Dashboard
   - Scaling

---

**Tudo que você precisa está aqui. Boa sorte! 🚀**
