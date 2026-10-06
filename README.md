# Data Quality API

API de observabilidade para acompanhar a saúde de tabelas, datasets e
pipelines de dados.

Este projeto trabalha em conjunto com o
[ETL Data Quality](https://github.com/davimatosms/etl-data-quality). O ETL
executa as validações; esta API recebe o resultado de cada execução,
calcula a atualidade do dado (*freshness*) e mantém um histórico consultável.

## O problema

Uma tabela pode estar tecnicamente disponível e ainda assim estar
desatualizada ou conter dados inválidos. Sem uma camada de observabilidade,
essa informação fica espalhada em logs, planilhas ou mensagens de operação.

A API responde centralmente:

- quando uma fonte foi verificada pela última vez;
- se ela está dentro da frequência esperada;
- se o último check passou nas regras de qualidade;
- quais foram os resultados dos checks anteriores;
- quais métricas foram produzidas pelo pipeline.

## Por que a API não executa as validações?

Essa é uma decisão de arquitetura. O pipeline é o componente que conhece o
formato, as regras e a tecnologia de processamento do dataset. A API não
precisa importar Pandas, Pandera, regras de CNPJ ou qualquer ferramenta
específica do pipeline.

Assim, os projetos ficam desacoplados:

- o ETL pode mudar suas regras ou sua ferramenta de processamento;
- outra fonte pode enviar checks usando outro job ou linguagem;
- a API permanece responsável apenas por registrar, consolidar e expor
  observabilidade.

## Arquitetura

```text
┌──────────────────────────┐
│ ETL Data Quality         │
│ extract                  │
│ validate                 │
│ transform                │
│ load                     │
└────────────┬─────────────┘
             │ POST /sources/{id}/checks
             ▼
┌──────────────────────────┐
│ Data Quality API         │
│ FastAPI + Pydantic       │
│ freshness sob consulta   │
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│ PostgreSQL               │
│ fontes + checks + regras │
└──────────────────────────┘
```

### Freshness

Freshness não é armazenado como um valor fixo. A cada consulta:

```text
sem check              → UNKNOWN
idade <= frequência × tolerância → FRESH
idade > frequência × tolerância  → STALE
```

A tolerância padrão é `1.5`. Ela absorve pequenos atrasos normais sem
classificar imediatamente a fonte como atrasada e pode ser configurada por
fonte.

## O que a API oferece

| Método | Endpoint | Finalidade |
|---|---|---|
| `POST` | `/sources` | Cadastra uma fonte monitorada |
| `GET` | `/sources` | Lista fontes com freshness e qualidade |
| `PUT` | `/sources/{id}` | Atualiza uma fonte |
| `DELETE` | `/sources/{id}` | Remove uma fonte e seu histórico |
| `POST` | `/sources/{id}/checks` | Recebe um resultado do pipeline |
| `GET` | `/sources/{id}/status` | Retorna status e últimos 10 checks |
| `GET` | `/health` | Verifica API e banco |
| `GET` | `/docs` | Abre o Swagger/OpenAPI |

### Cadastro de fonte

```json
{
  "name": "empresas",
  "description": "Cadastro de empresas processado diariamente",
  "expected_frequency_minutes": 1440,
  "freshness_tolerance": 1.5,
  "quality_rules": ["cnpj", "razao_social", "cep"]
}
```

### Check recebido

```json
{
  "checked_at": "2026-10-06T22:37:26Z",
  "status": "FAILING",
  "rule_results": [
    {
      "rule_name": "cnpj_duplicado",
      "passed": false,
      "message": "1 linha(s) rejeitada(s)"
    }
  ],
  "metrics": {
    "linhas_lidas": 3,
    "linhas_validas": 1,
    "linhas_rejeitadas": 2,
    "tempo_segundos": 0.235
  }
}
```

## Como executar com Docker

### Pré-requisitos

- Docker Desktop em execução;
- os dois projetos em diretórios irmãos:

```text
F:\Projetos\data-quality-api
F:\Projetos\etl-data-quality
```

### Demonstração integrada

Na pasta da API:

```powershell
docker compose up --build --abort-on-container-exit --exit-code-from etl-demo
```

O Compose sobe:

1. PostgreSQL da API;
2. API FastAPI;
3. PostgreSQL do ETL;
4. container de demonstração do ETL.

O `etl-demo` cadastra uma fonte, processa
`tests/fixtures/sample_dirty_data.csv`, grava os dados no banco do ETL e
envia o check para a API.

Para deixar a API disponível:

```powershell
docker compose up -d api api-db
```

Acesse <http://localhost:8000/docs>.

## Como executar sem o Compose integrado

### API

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Por padrão, o desenvolvimento local usa SQLite. Para PostgreSQL, defina:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://quality:quality@localhost:5432/data_quality"
```

### ETL conectado

Com a API rodando, cadastre a fonte e configure o ETL:

```powershell
$source = Invoke-RestMethod -Method Post `
  -Uri http://localhost:8000/sources `
  -ContentType "application/json" `
  -Body '{"name":"empresas","expected_frequency_minutes":1440,"freshness_tolerance":1.5,"quality_rules":["cnpj","razao_social","cep"]}'

cd ..\etl-data-quality
$env:QUALITY_API_URL = "http://localhost:8000"
$env:QUALITY_API_SOURCE_ID = $source.id
python -m src.pipeline --input tests/fixtures/sample_dirty_data.csv
```

O cliente do ETL usa timeout e retry. Se as variáveis não forem definidas,
o pipeline continua funcionando e gera apenas seu relatório local. Se apenas
uma variável for definida, a configuração é rejeitada explicitamente.

## Estrutura do projeto

```text
data-quality-api/
├── app/
│   ├── main.py                 # aplicação FastAPI e health check
│   ├── config.py               # configurações por ambiente
│   ├── db.py                   # engine e sessões SQLAlchemy
│   ├── models.py               # Source, Check e CheckRuleResult
│   ├── schemas.py              # contratos Pydantic
│   ├── routers/
│   │   ├── sources.py          # CRUD, status e visão geral
│   │   └── checks.py           # recebimento de checks
│   └── services/
│       └── freshness.py        # cálculo UNKNOWN/FRESH/STALE
├── tests/
├── checkpoints/                # rastreabilidade do plano
├── Dockerfile
├── docker-compose.yml          # API + ETL + dois bancos
├── requirements.txt
└── README.md
```

## Testes e qualidade

```powershell
python -m ruff check app tests
python -m pytest
```

Os testes cobrem:

- os estados `UNKNOWN`, `FRESH` e `STALE`;
- efeito da tolerância;
- cadastro, atualização e remoção de fontes;
- recebimento de checks;
- status e histórico;
- health check do banco.

O ETL possui sua própria suíte e teste de contrato do payload enviado à API.
O GitHub Actions executa lint e testes a cada push ou pull request.

## Escalabilidade e próximos incrementos

Para crescer além do MVP:

- adicionar Alembic para migrations;
- autenticar o cliente do ETL;
- adicionar paginação e filtros;
- criar índices compostos em `source_id` e `checked_at`;
- adicionar retenção de histórico;
- incluir métricas e alertas;
- executar o Compose integrado na CI.

## Projetos relacionados

- [ETL Data Quality](https://github.com/davimatosms/etl-data-quality):
  valida, transforma e carrega os dados.
- **Data Quality API**: registra os resultados e apresenta a saúde das fontes.

São projetos separados, mas fazem parte do mesmo sistema. A integração é
feita pelo contrato HTTP e pelo Compose de demonstração, não por
compartilhamento de código.
