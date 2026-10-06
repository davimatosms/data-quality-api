# Projeto 04 — API de Data Quality / Freshness Monitoring

[[davi-matos-marques-silva]]

## 1. Problema que resolve

Times de dados raramente confiam cegamente numa tabela — a pergunta
recorrente é "esse dado está atualizado?" e "esse dado passou nas
validações esperadas?". Sem uma resposta automatizada, isso vira
pergunta no Slack, planilha manual ou, pior, só é descoberto quando um
relatório sai errado.

Esse projeto prova que você entende observabilidade de dados — um tema
cada vez mais cobrado em vagas de backend + dados — construindo uma API
que expõe, de forma centralizada, a saúde de cada tabela/pipeline:
última atualização, se passou nas regras de qualidade, e há quanto
tempo isso é monitorado.

## 2. Escopo do MVP

- Cadastro de **fontes monitoradas** (tabela, pipeline ou dataset),
  cada uma com:
  - frequência esperada de atualização (ex. diária, horária),
  - regras de qualidade esperadas (ex. "sem nulos na coluna X",
    "contagem de linhas > 0", "sem duplicata na chave Y").
- Endpoint que as próprias fontes (ou um job agendado) chamam para
  **reportar um check**: timestamp, resultado de cada regra.
- Endpoint que calcula e expõe o **status atual**:
  - `FRESH` / `STALE` (baseado na frequência esperada vs. último check),
  - `PASSING` / `FAILING` (baseado nas regras de qualidade),
  - histórico dos últimos N checks.

## 3. Arquitetura

```
[Pipeline externo / Job agendado]
         │ reporta resultado do check
         ▼
   POST /sources/{id}/checks
         │
         ▼
   [API — FastAPI]
         │
         ├─► calcula freshness (agora - último check vs. frequência esperada)
         ├─► persiste resultado das regras de qualidade
         ▼
   [Postgres]
         │
         ▼
   GET /sources/{id}/status  ──► FRESH/STALE + PASSING/FAILING + histórico
   GET /sources             ──► visão geral de todas as fontes monitoradas
```

Princípios:
- **A API não roda as validações** — ela recebe o resultado de quem
  roda (o pipeline). Isso mantém a API simples e desacoplada de
  qualquer stack de processamento específica (importante: deixa claro
  no README que essa é uma decisão de design, não uma limitação).
- **Freshness é calculado, não armazenado**: o status "stale" é
  derivado do timestamp do último check comparado à frequência
  esperada, sempre que consultado — evita dado desatualizado sobre o
  próprio dado.
- **Histórico auditável**: cada check reportado fica guardado, não
  sobrescreve o anterior.

## 4. Integração com o ETL Data Quality

Esta API será consumida pelo projeto
`github.com/davimatosms/etl-data-quality`, que executa as etapas de
extract, validate, transform e load.

Após cada execução do ETL, o pipeline deve reportar à API:

- a fonte monitorada correspondente ao dataset/tabela processado;
- o timestamp da execução;
- o resultado de cada regra de qualidade;
- o status geral (`PASSING` ou `FAILING`);
- métricas complementares da execução, quando aplicável.

O ETL continua responsável por executar as validações e persistir os
dados tratados. A API atua como camada central de observabilidade,
recebendo os resultados via `POST /sources/{id}/checks`.

Requisitos da integração:

- definir um `Source` para cada dataset/tabela monitorado;
- padronizar o payload enviado pelo ETL;
- configurar a URL da API por variável de ambiente;
- implementar timeout, tratamento de erro e retry no cliente do ETL;
- executar os serviços em conjunto no Docker Compose para a demo;
- documentar a integração e o fluxo completo nos READMEs dos dois
  projetos.

## 5. Stack técnica

- **Linguagem/Framework:** Python + FastAPI (gera documentação
  OpenAPI automática — ótimo para o README, dá para linkar o Swagger)
- **Validação:** Pydantic (nativo do FastAPI)
- **Banco:** PostgreSQL
- **ORM:** SQLAlchemy
- **Agendamento (opcional, fase 2):** um script simples com `cron`/
  APScheduler que simula pipelines externos reportando checks
  periodicamente, para a demo ficar viva
- **Testes:** pytest + httpx (TestClient do FastAPI)
- **Containerização:** Docker + docker-compose
- **CI:** GitHub Actions

## 6. Estrutura de pastas sugerida

```
data-quality-api/
├── docker-compose.yml
├── Dockerfile
├── README.md
├── app/
│   ├── main.py
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── routers/
│   │   ├── sources.py
│   │   └── checks.py
│   └── services/
│       └── freshness.py     # lógica de cálculo FRESH/STALE
├── scripts/
│   └── simulate_checks.py   # simula pipelines reportando checks
└── tests/
    ├── test_freshness.py
    └── test_sources_api.py
```

## 7. Modelo de dados (núcleo)

- **Source**: id, nome, descrição, frequência esperada (ex. em minutos),
  regras de qualidade esperadas (lista de nomes/descrições).
- **Check**: source_id, timestamp, resultados por regra (JSON ou tabela
  separada `check_rule_result`), status geral do check (PASSING/
  FAILING).

## 8. Lógica de freshness (núcleo do projeto)

```
status_freshness(source):
    último_check = buscar check mais recente da source
    se não existe nenhum check:
        retorna "UNKNOWN"
    tempo_desde_ultimo = agora - último_check.timestamp
    se tempo_desde_ultimo > source.frequencia_esperada * tolerância:
        retorna "STALE"
    senão:
        retorna "FRESH"
```

A `tolerância` (ex. 1.5x a frequência esperada, para absorver atrasos
pequenos) deve ser configurável por source — é um bom ponto para
explicar no README por que existe.

## 9. Passo a passo de implementação

1. **Setup**: projeto FastAPI, docker-compose com Postgres.
2. **Models**: `Source`, `Check`, `CheckRuleResult`.
3. **Endpoints de Source**: CRUD básico de fontes monitoradas.
4. **Endpoint de Check**: `POST /sources/{id}/checks` recebe o
   resultado reportado.
5. **Serviço de freshness**: lógica da seção 7, com testes cobrindo os
   três estados (FRESH/STALE/UNKNOWN) e o efeito da tolerância.
6. **Endpoint de status**: `GET /sources/{id}/status` combinando
   freshness + resultado das regras de qualidade do último check.
7. **Endpoint de visão geral**: `GET /sources` com status resumido de
   todas as fontes — essa é a "tela" que simula um dashboard sem
   precisar de frontend.
8. **Script de simulação**: `simulate_checks.py` reportando checks
   periódicos (com alguma fonte propositalmente ficando stale ou
   failing) para a demo do README ter algo visível.
9. **Integração com o ETL**: adicionar no `etl-data-quality` um cliente
   para registrar fontes e reportar o resultado de cada execução na API.
10. **Execução integrada**: conectar os dois projetos via Docker Compose,
    variáveis de ambiente e rede compartilhada.
11. **Testes**: unitários (freshness) + de API (httpx TestClient) +
    teste de contrato do payload enviado pelo ETL.
12. **CI**: GitHub Actions.
13. **README**: problema → arquitetura → integração com o ETL → como rodar → decisões técnicas
    (por que a API não executa validações) → link para o Swagger
    (`/docs` do FastAPI, print ou GIF).

## 10. Decisões técnicas a documentar no README (diferencial)

- Por que a API recebe resultados em vez de executar as checagens
  (desacoplamento de stack de processamento).
- Por que freshness é calculado em tempo de consulta, não armazenado.
- Como a tolerância evita falsos positivos de "stale" por pequenos
  atrasos esperados.
- Como isso escalaria para dezenas/centenas de fontes monitoradas (ex.
  índice em `source_id + timestamp`, paginação no `GET /sources`).
- Como o ETL reporta sucesso e falha sem transferir a responsabilidade
  de validação para a API.

## 11. Critério de "pronto para fixar no GitHub"

- [ ] `docker compose up` sobe API + banco.
- [ ] Cadastro de fonte, reporte de check e consulta de status
      funcionando ponta a ponta.
- [ ] O `etl-data-quality` reporta automaticamente o resultado de uma
      execução para a API.
- [ ] O ETL usa `QUALITY_API_URL` e `QUALITY_API_SOURCE_ID`, com timeout,
      retry e falha explícita quando a configuração está incompleta.
- [x] Os dois projetos sobem e se comunicam via Docker Compose integrado.
- [ ] Script de simulação populando dados de forma que o `/docs`
      (Swagger) mostre algo real ao abrir.
- [ ] Testes cobrindo os três estados de freshness.
- [ ] CI verde.
- [ ] README completo, com link/print do Swagger.
