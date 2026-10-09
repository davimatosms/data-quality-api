# Plano de implementação: Data Quality API

**Data:** 2026-10-06 | **Especificação:** `data-quality-api.md`

## Resumo

Construir uma API FastAPI que centraliza o monitoramento de datasets
processados pelo `etl-data-quality`. O ETL executa as validações e envia
checks; a API persiste o histórico e calcula freshness sob consulta.

## Requisitos

- **REQ-001:** cadastrar e consultar fontes monitoradas.
- **REQ-002:** receber checks do ETL com timestamp, regras e status.
- **REQ-003:** calcular `UNKNOWN`, `FRESH` ou `STALE` com tolerância por fonte.
- **REQ-004:** expor status de freshness, qualidade e histórico.
- **REQ-005:** disponibilizar visão geral de todas as fontes.
- **REQ-006:** permitir execução local com PostgreSQL/Docker.
- **REQ-007:** testar regras de freshness, API e contrato de integração.
- **REQ-008:** documentar integração, decisões técnicas e execução.

## Contexto técnico

- Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2 e PostgreSQL.
- Testes com pytest e TestClient/httpx.
- `DATABASE_URL` configurável; SQLite é usado apenas nos testes.
- O ETL reportará para `POST /sources/{id}/checks` usando URL configurável,
  timeout e retry.

## Etapas

### Fase 1 — Fundação

- **P1.1 [REQ-001, REQ-006]:** criar configuração, conexão SQLAlchemy,
  modelos e migração inicial automática.
- **P1.2 [REQ-001]:** implementar CRUD de fontes.

### Fase 2 — Monitoramento

- **P2.1 [REQ-002]:** implementar recebimento e persistência de checks.
- **P2.2 [REQ-003, REQ-004]:** implementar serviço de freshness e status.
- **P2.3 [REQ-005]:** implementar visão geral resumida.

### Fase 3 — Integração e qualidade

- **P3.1 [REQ-007]:** adicionar testes unitários, de API e contrato do payload.
- **P3.2 [REQ-006]:** adicionar Dockerfile e Docker Compose.
- **P3.3 [REQ-008]:** documentar fluxo API ↔ ETL, Swagger e decisões.
- **P3.4 [REQ-008]:** adicionar CI com lint e testes.

## Tarefas

- [ ] T001 [Plan:1.1] Criar configuração e conexão em `app/config.py` e `app/db.py`.
- [ ] T002 [Plan:1.1] Criar modelos `Source`, `Check` e `CheckRuleResult` em `app/models.py`.
- [x] T003 [Plan:1.2] Criar schemas e CRUD de fontes em `app/routers/sources.py`.
- [x] T004 [Plan:2.1] Criar schema e endpoint de checks em `app/routers/checks.py`.
- [x] T005 [Plan:2.2] Implementar cálculo de freshness em `app/services/freshness.py`.
- [x] T006 [Plan:2.2,2.3] Implementar endpoints de status e visão geral.
- [x] T007 [P] [Plan:3.1] Cobrir freshness em `tests/test_freshness.py`.
- [x] T008 [P] [Plan:3.1] Cobrir endpoints em `tests/test_api.py`.
- [x] T009 [Plan:3.2] Criar `Dockerfile`, `docker-compose.yml` e `.env.example`.
- [x] T010 [Plan:3.3] Documentar execução e integração no `README.md`.
- [x] T011 [P] [Plan:3.4] Configurar workflow em `.github/workflows/ci.yml`.

## Estrutura

```text
app/
  main.py
  config.py
  db.py
  models.py
  schemas.py
  routers/{sources,checks}.py
  services/freshness.py
tests/{test_freshness,test_api}.py
```

## Estratégia de testes

- Unitários: `UNKNOWN`, `FRESH`, `STALE` e tolerância.
- API: criação/listagem de fonte, envio de check e status.
- Contrato: payload enviado pelo ETL validado por Pydantic.
- Aceite: `pytest` verde e fluxo Docker documentado.

## Requirement Mapping

| REQ ID | Plan items | Evidência |
|---|---|---|
| REQ-001 | P1.1, P1.2 | `app/models.py`, `app/routers/sources.py` |
| REQ-002 | P2.1 | `app/schemas.py`, `app/routers/checks.py` |
| REQ-003 | P2.2 | `app/services/freshness.py` |
| REQ-004 | P2.2 | `GET /sources/{id}/status` |
| REQ-005 | P2.3 | `GET /sources` |
| REQ-006 | P1.1, P3.2 | `Dockerfile`, `docker-compose.yml` |
| REQ-007 | P3.1 | `tests/` |
| REQ-008 | P3.3, P3.4 | `README.md`, `.github/workflows/ci.yml` |
