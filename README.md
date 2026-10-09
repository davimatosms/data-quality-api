# Data Quality API

Observability API that tracks the health of tables, datasets, and data
pipelines.

[![CI](https://github.com/davimatosms/data-quality-api/actions/workflows/ci.yml/badge.svg)](https://github.com/davimatosms/data-quality-api/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Python · FastAPI · Pydantic · SQLAlchemy · PostgreSQL · Docker · GitHub Actions

> Educational MVP built with production-oriented practices. No real users,
> intentionally small enough to run locally.

> **Part of a two-repo system.** This project works together with
> [ETL Data Quality](https://github.com/davimatosms/etl-data-quality):
> the ETL runs the validations, the API tracks the health of each run.

## Table of contents

- [The problem](#the-problem)
- [Architecture](#architecture)
- [Quick start](#quick-start)
- [Quick start with Docker](#quick-start-with-docker)
- [Usage](#usage)
- [Technical decisions](#technical-decisions)
- [Testing and quality](#testing-and-quality)
- [Project structure](#project-structure)
- [Known limitations and next steps](#known-limitations-and-next-steps)
- [Project documentation](#project-documentation)
- [Related projects](#related-projects)
- [License](#license)

## The problem

A table can be technically available and still be stale or contain invalid
data. Without an observability layer, that information ends up scattered
across logs, spreadsheets, or operations messages.

The API answers:

- when a source was last checked;
- whether it is within the expected frequency;
- whether the latest check passed the quality rules;
- what the results of previous checks were;
- which metrics the pipeline produced.

## Architecture

```text
┌──────────────────────────┐
│ ETL Data Quality         │
│ extract → validate →     │
│ transform → load         │
└────────────┬─────────────┘
             │ POST /sources/{id}/checks
             ▼
┌──────────────────────────┐
│ Data Quality API         │
│ FastAPI + Pydantic       │
│ freshness on read        │
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│ PostgreSQL               │
│ sources + checks + rules │
└──────────────────────────┘
```

### Data freshness

Freshness is not stored as a fixed value. It is calculated on every read:

```text
no check yet                    → UNKNOWN
age <= frequency × tolerance    → FRESH
age >  frequency × tolerance    → STALE
```

The default freshness tolerance is `1.5`. It absorbs small, normal delays
without immediately classifying a source as stale and can be configured per
source.

## Quick start

### Prerequisites

- Python 3.12 or newer;
- Docker Desktop, when running the integrated demo;
- the two projects cloned into sibling directories:

```text
data-quality-api/
etl-data-quality/
```

### Run the API locally

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

<details>
<summary>Windows (PowerShell)</summary>

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

</details>

The local default is SQLite. Open <http://localhost:8000/docs> to try the
interactive Swagger/OpenAPI documentation.

## Quick start with Docker

From the API repository:

```bash
docker compose up --build --abort-on-container-exit --exit-code-from etl-demo
```

<details>
<summary>Windows (PowerShell)</summary>

```powershell
docker compose up --build --abort-on-container-exit --exit-code-from etl-demo
```

</details>

The integrated Compose setup starts:

1. PostgreSQL for the API;
2. the FastAPI application;
3. PostgreSQL for the ETL;
4. the ETL demonstration container.

The `etl-demo` container registers a source, processes
`tests/fixtures/sample_dirty_data.csv`, stores the ETL data, and sends the
check to the API. To leave the API available after the demo:

```bash
docker compose up -d api api-db
```

<details>
<summary>Windows (PowerShell)</summary>

```powershell
docker compose up -d api api-db
```

</details>

Open <http://localhost:8000/docs> for the Swagger UI.

## Usage

### Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/sources` | Register a monitored source |
| `GET` | `/sources` | List sources with freshness and quality |
| `PUT` | `/sources/{id}` | Update a source |
| `DELETE` | `/sources/{id}` | Delete a source and its history |
| `POST` | `/sources/{id}/checks` | Receive a pipeline result |
| `GET` | `/sources/{id}/status` | Return status and the last 10 checks |
| `GET` | `/health` | Check API and database health |
| `GET` | `/docs` | Open Swagger/OpenAPI |

The [Swagger UI](http://localhost:8000/docs) provides an interactive view of
these endpoints and their request and response schemas.

### Registering a source

```bash
curl -X POST http://localhost:8000/sources \
  -H "Content-Type: application/json" \
  -d '{"name":"empresas","expected_frequency_minutes":1440,"freshness_tolerance":1.5,"quality_rules":["cnpj","razao_social","cep"]}'
```

<details>
<summary>Windows (PowerShell)</summary>

```powershell
$body = @{
  name = "empresas"
  expected_frequency_minutes = 1440
  freshness_tolerance = 1.5
  quality_rules = @("cnpj", "razao_social", "cep")
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
  -Uri http://localhost:8000/sources `
  -ContentType "application/json" `
  -Body $body
```

</details>

Example response from `GET /sources/{id}/status`:

```json
{
  "source_id": 1,
  "freshness": "FRESH",
  "quality": "PASSING",
  "latest_check": {
    "id": 1,
    "checked_at": "2026-10-06T22:37:26Z",
    "status": "PASSING",
    "rule_results": [
      {
        "rule_name": "cnpj",
        "passed": true,
        "message": null
      }
    ],
    "metrics": {
      "linhas_lidas": 3,
      "linhas_validas": 3,
      "linhas_rejeitadas": 0,
      "tempo_segundos": 0.235
    }
  },
  "history": [
    {
      "id": 1,
      "checked_at": "2026-10-06T22:37:26Z",
      "status": "PASSING",
      "rule_results": [
        {
          "rule_name": "cnpj",
          "passed": true,
          "message": null
        }
      ],
      "metrics": {
        "linhas_lidas": 3,
        "linhas_validas": 3,
        "linhas_rejeitadas": 0,
        "tempo_segundos": 0.235
      }
    }
  ]
}
```

### Check payload

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

The metric keys and messages remain in Portuguese because they are part of
the current Brazilian dataset integration contract. Domain identifiers such
as `cnpj`, `razao_social`, `cep`, and `empresas` are also intentionally kept
in their original form.

### Connecting the ETL

With the API running, register a source and configure the ETL client:

```bash
source_id=$(curl -s -X POST http://localhost:8000/sources \
  -H "Content-Type: application/json" \
  -d '{"name":"empresas","expected_frequency_minutes":1440,"freshness_tolerance":1.5,"quality_rules":["cnpj","razao_social","cep"]}' \
  | python -c "import json, sys; print(json.load(sys.stdin)['id'])")

cd ../etl-data-quality
export QUALITY_API_URL="http://localhost:8000"
export QUALITY_API_SOURCE_ID="$source_id"
python -m src.pipeline --input tests/fixtures/sample_dirty_data.csv
```

<details>
<summary>Windows (PowerShell)</summary>

```powershell
$source = Invoke-RestMethod -Method Post `
  -Uri http://localhost:8000/sources `
  -ContentType "application/json" `
  -Body '{"name":"empresas","expected_frequency_minutes":1440,"freshness_tolerance":1.5,"quality_rules":["cnpj","razao_social","cep"]}'

Set-Location ..\etl-data-quality
$env:QUALITY_API_URL = "http://localhost:8000"
$env:QUALITY_API_SOURCE_ID = $source.id
python -m src.pipeline --input tests/fixtures/sample_dirty_data.csv
```

</details>

The ETL client uses timeout and retry. If the variables are not defined, the
pipeline continues to work and produces only its local report. If only one
variable is defined, the configuration is rejected explicitly.

## Technical decisions

### Why the API does not run validations

The pipeline knows the dataset format, quality rules, and processing
technology. The API only needs to register, consolidate, and expose
observability. This keeps the projects decoupled: the ETL can change its
rules or processing tool, and another source can send checks from a different
job or language.

### Why freshness is calculated on read

Freshness changes as time passes even when no new data is written. Calculating
it when a source is queried avoids stale derived values and keeps the stored
model focused on facts such as check timestamps and configured frequency.

### Why tolerance is configurable per source

Different sources have different delivery schedules and operational
variability. A per-source freshness tolerance avoids forcing one global
threshold onto unrelated pipelines.

### Delete behavior

`DELETE /sources/{id}` removes the source and its check history. This keeps
the database from retaining orphaned operational records, but it also means
deletion is destructive and should be protected by an authorization layer in
a production system.

### SQLite locally, PostgreSQL in Compose

SQLite keeps the local setup small and dependency-free. The integrated Compose
environment uses PostgreSQL to exercise the database engine and deployment
shape closer to a production setup.

## Testing and quality

```bash
python -m ruff check app tests
python -m pytest
```

<details>
<summary>Windows (PowerShell)</summary>

```powershell
python -m ruff check app tests
python -m pytest
```

</details>

The tests cover:

- `UNKNOWN`, `FRESH`, and `STALE` freshness states;
- the effect of freshness tolerance;
- source creation, update, and deletion;
- check ingestion;
- status and history;
- database health.

GitHub Actions runs Ruff and pytest on every push and pull request.

## Project structure

```text
data-quality-api/
├── app/
│   ├── main.py                 # FastAPI application and health check
│   ├── config.py               # environment-based settings
│   ├── db.py                   # SQLAlchemy engine and sessions
│   ├── models.py               # Source, Check, and CheckRuleResult
│   ├── schemas.py              # Pydantic contracts
│   ├── routers/
│   │   ├── sources.py          # CRUD, status, and overview
│   │   └── checks.py           # check ingestion
│   └── services/
│       └── freshness.py        # UNKNOWN/FRESH/STALE calculation
├── tests/
├── docs/                       # planning notes and original specification
├── .env.example
├── .github/workflows/ci.yml
├── Dockerfile
├── docker-compose.yml          # API + ETL + two databases
├── LICENSE
├── requirements.txt
└── README.md
```

## Known limitations and next steps

### Current limitations

- no authentication between the ETL client and the API;
- no database migrations;
- no pagination for source or check history endpoints.

### Next steps

- add Alembic migrations;
- add authentication and authorization;
- add composite indexes for `source_id` and `checked_at`;
- add history retention policies;
- expose metrics and alerts;
- run the integrated Compose flow in CI.

## Project documentation

Planning notes and the original specification live in [`docs/`](docs/).

## Related projects

- [ETL Data Quality](https://github.com/davimatosms/etl-data-quality):
  validates, transforms, and loads the data.

The projects are separate but form one system. Integration happens through
the HTTP contract and the demonstration Compose setup, not through shared
source code.

## License

This project is licensed under the [MIT License](LICENSE).
