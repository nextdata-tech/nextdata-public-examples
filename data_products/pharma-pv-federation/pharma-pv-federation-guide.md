# pharma-pv-federation — Architecture & Operating Guide

## What it is

`pharma-pv-federation` is a **federation orchestrator** data product on the Nextdata (nxd) platform. It does not copy or move data. It exposes two MCP tools that let an AI agent (or any MCP client, e.g. Power BI) run **cross-domain pharmacovigilance queries** over two independently-governed source data products that live in Snowflake — joining adverse-event counts against prescription volumes **in place, at read time**, to compute the adverse-event reporting rate per 1,000 prescriptions.

The point of the product is a single insight that no one source can give you on its own: **raw event counts and exposure-normalised rates rank products in opposite order**, and the inversion is the finding.

---

## Architecture

```
  ┌──────────────────────────────────────────────────────────────────┐
  │  CONSUMER         Claude / AI agent   ·   Power BI (MCP connector) │
  └───────────────────────────────┬──────────────────────────────────┘
                                   │  natural language ↔ MCP tools/call
  ┌───────────────────────────────▼──────────────────────────────────┐
  │  FEDERATION       nxd MCP Proxy  (discovery, routing, auth)        │
  │  & GOVERNANCE     ───────────────────────────────────────────     │
  │                   pharma-pv-federation  ORCHESTRATOR (RPC pod)     │
  │                     • get_metadata            • execute_federated… │
  │                     (no data of its own — just the two tools)      │
  └───────────────────────────────┬──────────────────────────────────┘
                                   │  Snowflake REST + SQL_EXEC_MCP_SRVR
  ┌───────────────────────────────▼──────────────────────────────────┐
  │  COMPUTE / DATA   Snowflake  (PARTNER_AZ_DB)                       │
  │                                                                    │
  │     DRUG_SAFETY_SIGNALS                COMMERCIAL_PRESCRIPTIONS     │
  │       .ADVERSE_EVENT_SUMMARY             .PRESCRIPTION_VOLUME       │
  │       (numerator)                        (denominator)             │
  │            ▲ governed by                      ▲ governed by         │
  │       drug-safety-signals DP            commercial-prescriptions DP │
  └────────────────────────────────────────────────────────────────────┘
```

Three things make this a *mesh* design rather than a pipeline:

1. **The orchestrator owns no pharmacovigilance data.** It carries one tiny anchor table (`PV_REGISTRY`) whose only job is to make the platform hand the pod live Snowflake credentials.
2. **The two source tables stay under their own data products' governance.** The federation reads them where they live; nothing is ETL'd into the orchestrator.
3. **Execution is borrowed, not bespoke.** The tools drive Snowflake's `SQL_EXEC_MCP_SRVR` under the `ACCOUNT_COVERAGE` schema — a proven execution endpoint whose role can read every schema in `PARTNER_AZ_DB`, so the cross-schema join runs without new grants.

### The two source tables (live schema)

| Table | Role | Columns that matter |
|---|---|---|
| `DRUG_SAFETY_SIGNALS.ADVERSE_EVENT_SUMMARY` | numerator | `PRODUCT_ID`, `REGION`, `REPORT_PERIOD`, **`ADVERSE_EVENT_COUNT`**, `SERIOUS_EVENT_COUNT`, `DEATH_COUNT`, … |
| `COMMERCIAL_PRESCRIPTIONS.PRESCRIPTION_VOLUME` | denominator | `PRODUCT_ID`, `REGION`, `REPORT_PERIOD`, **`TOTAL_PRESCRIPTIONS`**, `PATIENT_COUNT`, … |

- **Join keys:** `PRODUCT_ID`, `REGION`, `REPORT_PERIOD` (all three).
- **Metric:** `1000.0 * SUM(adverse_event_count) / NULLIF(SUM(total_prescriptions), 0)`.

---

## Components

The data product is seven files. Reading order mirrors how a request flows.

### `spec.py` — the product definition

Declares the Snowflake transform (the credential anchor), the **`snowflake` output port** (writes `PV_REGISTRY`), and the **`mcp-api` RPC port** that publishes the two tools. Abridged:

```python
spec = (
    data_product(name="pharma-pv-federation", domain="LIFE-SCIENCES/PHARMACOVIGILANCE", ...)
    .transform(sql("transform/build_pv_registry.sql").compute(SNOWFLAKE_SERVICE))
    # Output 1: the anchor table that gives this DP live Snowflake credentials
    .output(
        data_product_output().promise(pv_registry).port(
            "snowflake",
            storage(SNOWFLAKE_SERVICE).config(
                snowflake_config("PHARMA_PV_FEDERATION").target_table("PV_REGISTRY", pv_registry))))
    # Output 2: the MCP endpoint that exposes the two tools
    .output(
        data_product_rpc_output()
        .function(rpc_function(code(get_metadata),           get_metadata_request,           get_metadata_response).description("..."))
        .function(rpc_function(code(execute_federated_query), execute_federated_query_request, execute_federated_query_response).description("..."))
        .port("mcp-api", rpc_server(MCP_API_SERVICE).enable_endpoints().mcp_path("/mcp")))
    .control("owner", owner().user("hello@nextdata.com")))
```

### `transform/build_pv_registry.sql` — the credential anchor

One constant row. It reads **no** other schema and counts **no** upstream rows, so deployment can never fail on an empty or not-yet-visible source table. `CREATE OR REPLACE` makes it self-healing if the model's columns ever change.

```sql
CREATE OR REPLACE TABLE {{ outputs["snowflake"].pv_registry }} AS
SELECT 'pharma-pv-federation'                                              AS registry_id,
       'PARTNER_AZ_DB.DRUG_SAFETY_SIGNALS.ADVERSE_EVENT_SUMMARY'           AS safety_source,
       'PARTNER_AZ_DB.COMMERCIAL_PRESCRIPTIONS.PRESCRIPTION_VOLUME'        AS commercial_source,
       'product_id, region, report_period'                                AS join_keys,
       '1000.0 * SUM(adverse_event_count) / NULLIF(SUM(total_prescriptions),0)' AS rate_metric,
       CURRENT_TIMESTAMP()::STRING                                         AS built_at;
```

### `__mcp__.py` — the two tools + the execution helper

This is the heart of the product. Each tool is a function injected with `snowflake` (the live credential context from the output port) and the request.

```python
@function(name="execute_federated_query")
@mcp.tool(name="execute_federated_query", description="...")
def execute_federated_query(snowflake: Snowflake, request: Request) -> Response:
    from nxd.drivers.rpc import Response            # re-imported locally (see Design notes)
    sql = (request.get("sql") or "").strip().rstrip(";").strip()
    if not (sql.lower().startswith("select") or sql.lower().startswith("with")):
        return Response({"result": "ERROR: only read-only SELECT/WITH allowed.", "row_count": "0"})
    # ... block ';', INSERT/UPDATE/DELETE/DDL ; strip a trailing LIMIT ...
    result_text = _run_sql_via_snowflake_mcp(snowflake, sql, "pharma-pv-execute-federated-query")
    row_count = str(max(len(result_text.splitlines()) - 1, 0))   # data rows = lines − header
    return Response({"result": result_text, "row_count": row_count})
```

The shared helper performs the Snowflake handshake. It uses the injected credentials, then drives `SQL_EXEC_MCP_SRVR`:

```python
def _run_sql_via_snowflake_mcp(snowflake, sql, client_name):
    import requests as req
    account  = snowflake.account.replace("_", "-").lower()
    base_url = f"https://{account}.snowflakecomputing.com"
    mcp_url  = f"{base_url}/api/v2/databases/PARTNER_AZ_DB/schemas/ACCOUNT_COVERAGE/mcp-servers/SQL_EXEC_MCP_SRVR"

    # 1. login  -> session token
    token = req.post(f"{base_url}/session/v1/login-request",
                     params={"warehouse": snowflake.warehouse, "databaseName": snowflake.database,
                             "schemaName": snowflake.schema},
                     json={"data": {"LOGIN_NAME": snowflake.user, "PASSWORD": snowflake.password}}
                    ).json()["data"]["token"]
    headers = {"Authorization": f'Snowflake Token="{token}"',
               "Accept": "application/json, text/event-stream"}

    # 2. initialize (capture Mcp-Session-Id)   3. notifications/initialized
    # 4. tools/call -> sql_exec_tool  (argument key MUST be "sql")
    call = req.post(mcp_url, headers=headers, json={
        "jsonrpc": "2.0", "id": "2", "method": "tools/call",
        "params": {"name": "sql_exec_tool", "arguments": {"sql": sql}}})
    return _render_result(_extract_text(call))      # JSON or SSE -> clean table
```

`_render_result` turns Snowflake's `result_set` JSON into a tab-separated table so the agent gets rows, not a blob:

```python
rs   = json.loads(text)["result_set"]
cols = [c["name"] for c in rs["resultSetMetaData"]["rowType"]]
return "\n".join(["\t".join(cols)] + ["\t".join(map(str, row)) for row in rs["data"]])
```

### Supporting files

- **`models.py`** — defines `pv_registry` (the anchor model: `registry_id`, `safety_source`, … all `string`).
- **`nxd_models.py` / `nxd_spec.py`** — import the primitives, models, and tool functions and re-export them via `__all__`. `nxd_models.py` deliberately does **not** import `Predicate` (no glossary on the orchestrator).
- **`requirements.txt`** — just `requests==2.31.0`.

---

## The two MCP tools

| Tool | Call it… | What it returns |
|---|---|---|
| **`get_metadata`** | **first** | Live `INFORMATION_SCHEMA` columns + comments for both tables, the join keys, and the rate-metric formula. Takes a `database` argument (required but nullable — pass `null` or a name; defaults to `PARTNER_AZ_DB`). |
| **`execute_federated_query`** | after metadata | Runs one read-only `SELECT`/`WITH` in Snowflake and returns the result as a table plus a `row_count`. Reject anything that isn't a single read-only statement. |

Because `get_metadata` returns the *real* schema, the agent writes its own SQL — it is never limited to a fixed list of questions.

---

## Lifecycle of a natural-language query

```mermaid
sequenceDiagram
    participant U as User
    participant A as Claude (agent)
    participant P as nxd MCP Proxy
    participant D as Orchestrator RPC pod
    participant S as Snowflake (SQL_EXEC_MCP_SRVR)

    U->>A: "Which product has the highest AE rate per 1,000 Rx?"
    A->>P: tools/call get_metadata
    P->>D: invoke (nxd injects Snowflake credentials)
    D->>S: login → initialize → sql_exec_tool(INFORMATION_SCHEMA)
    S-->>D: result_set JSON
    D-->>A: rendered schema + join keys + metric
    A->>A: author cross-domain JOIN SQL
    A->>P: tools/call execute_federated_query(sql)
    P->>D: invoke (credentials injected again)
    D->>D: validate read-only · strip trailing LIMIT
    D->>S: login → initialize → sql_exec_tool(JOIN)
    S-->>D: result_set JSON
    D->>D: render to table + row_count
    D-->>A: clean rows
    A-->>U: "IMMUNADEX (EU) tops at 27.78/1k; NEURVANTA has the most raw events but the lowest rate"
```

Step by step:

1. **Intent → tool.** The user asks in plain language; the agent picks the `pharma-pv-federation` tools from the proxy.
2. **Schema first.** The agent calls `get_metadata`. The proxy routes it to the orchestrator's RPC pod, and nxd **injects the Snowflake credential context** into the function.
3. **Borrowed execution.** The pod logs into Snowflake, runs the MCP handshake (`login → initialize → notifications/initialized → tools/call`), and asks `sql_exec_tool` to read `INFORMATION_SCHEMA`. The result comes back, gets rendered, and the agent now knows the real columns, join keys, and metric.
4. **SQL authoring.** The agent writes the cross-domain join itself.
5. **Guarded execution.** `execute_federated_query` validates the statement is a single read-only `SELECT`/`WITH`, strips a trailing `LIMIT` (Snowflake's server appends its own), and runs it through the same handshake.
6. **Render & return.** Snowflake's `result_set` JSON is rendered into a table with a row count and returned through the proxy to the agent, which states the answer in business terms.

---

## Worked examples

### 1. Inspect the schema (`get_metadata`)

> *"What can I query in pharma-pv-federation?"*

Returns the live columns of both tables with comments, e.g.:

```
TABLE_SCHEMA              TABLE_NAME             COLUMN_NAME          DATA_TYPE  COMMENT
DRUG_SAFETY_SIGNALS       ADVERSE_EVENT_SUMMARY  ADVERSE_EVENT_COUNT  NUMBER     Total adverse-event reports — numerator
COMMERCIAL_PRESCRIPTIONS  PRESCRIPTION_VOLUME    TOTAL_PRESCRIPTIONS  NUMBER     Total prescriptions (TRx) — exposure denominator
...
--- FEDERATION GUIDE ---
Join keys: product_id, region, report_period
Key metric: 1000.0 * SUM(adverse_event_count) / NULLIF(SUM(total_prescriptions), 0)
```

### 2. The headline: reporting rate by product and region (the inversion)

> *"Which product has the highest adverse-event rate per 1,000 prescriptions, and how does that compare to raw event counts?"*

SQL the agent runs via `execute_federated_query`:

```sql
SELECT s.product_name, s.region,
       SUM(s.adverse_event_count)  AS total_ae,
       SUM(c.total_prescriptions)  AS total_rx,
       ROUND(1000.0 * SUM(s.adverse_event_count)
             / NULLIF(SUM(c.total_prescriptions), 0), 2) AS ae_per_1k_rx
FROM PARTNER_AZ_DB.DRUG_SAFETY_SIGNALS.ADVERSE_EVENT_SUMMARY s
JOIN PARTNER_AZ_DB.COMMERCIAL_PRESCRIPTIONS.PRESCRIPTION_VOLUME c
  ON s.product_id = c.product_id
 AND s.region     = c.region
 AND s.report_period = c.report_period
GROUP BY s.product_name, s.region
ORDER BY ae_per_1k_rx DESC
```

Live output:

```
PRODUCT_NAME  REGION         TOTAL_AE  TOTAL_RX    AE_PER_1K_RX
IMMUNADEX     Europe         3125      112500      27.78
IMMUNADEX     North America  5025      195000      25.77
VELORIN       Europe         10150     675000      15.04
RYSALDA       Asia-Pacific   3300      412500       8.00
RYSALDA       Europe         9000      1200000      7.50
RYSALDA       North America  12575     1800000      6.99
VELORIN       Asia-Pacific   1650      267500       6.17
VELORIN       North America  33750     6750000      5.00
NEURVANTA     Asia-Pacific   16350     4675000      3.50
NEURVANTA     Europe         29200     9175000      3.18
NEURVANTA     North America  45000     15000000     3.00
```

Read it: **NEURVANTA (North America) has the most raw adverse events of any row — 45,000 — yet the *lowest* rate (3.00/1k)** because its exposure is enormous (15M Rx). **IMMUNADEX (Europe) has ~14× fewer raw events but ~9× the rate.** Ranking by count and ranking by rate are opposite — that is the signal.

### 3. Region comparison for one product

> *"Compare IMMUNADEX's reporting rate across regions."*

```sql
SELECT s.region,
       SUM(s.adverse_event_count) AS total_ae,
       SUM(c.total_prescriptions) AS total_rx,
       ROUND(1000.0 * SUM(s.adverse_event_count)
             / NULLIF(SUM(c.total_prescriptions), 0), 2) AS ae_per_1k_rx
FROM PARTNER_AZ_DB.DRUG_SAFETY_SIGNALS.ADVERSE_EVENT_SUMMARY s
JOIN PARTNER_AZ_DB.COMMERCIAL_PRESCRIPTIONS.PRESCRIPTION_VOLUME c
  ON s.product_id = c.product_id AND s.region = c.region AND s.report_period = c.report_period
WHERE s.product_name = 'IMMUNADEX'
GROUP BY s.region
ORDER BY ae_per_1k_rx DESC
```

### 4. Seriousness lens (a different numerator)

> *"Which products have the highest share of serious adverse events?"*

```sql
SELECT s.product_name,
       SUM(s.serious_event_count) AS serious_ae,
       SUM(s.adverse_event_count) AS total_ae,
       ROUND(100.0 * SUM(s.serious_event_count)
             / NULLIF(SUM(s.adverse_event_count), 0), 1) AS pct_serious
FROM PARTNER_AZ_DB.DRUG_SAFETY_SIGNALS.ADVERSE_EVENT_SUMMARY s
GROUP BY s.product_name
ORDER BY pct_serious DESC
```

> **Tip for whoever drives the tools:** always let `get_metadata` run first, use fully-qualified table names, and never append a trailing `LIMIT` — the server paginates for you.

---

## Design notes (the non-obvious bits)

These are the constraints that make the product deploy and run reliably on nxd + Snowflake:

- **Constants live inside functions, not at module scope.** nxd extracts each tool into its own generated module on the RPC pod, carrying module-level *imports* and *`def`s* but **not** bare constant assignments. A module-level `FED_DB = "…"` referenced inside a tool becomes a `NameError` at runtime. Every literal is therefore a local; the shared handshake stays a module-level `def` (which does survive).
- **The `sql_exec_tool` argument key is `sql`.** Passing `query` yields *"sql request parameter is required and cannot be empty."*
- **Read-only by construction.** `execute_federated_query` only accepts a single `SELECT`/`WITH`; it blocks `;` and any DDL/DML keyword before a statement ever reaches Snowflake.
- **Strip a trailing `LIMIT`.** Snowflake's MCP server appends its own; a user-supplied one collides.
- **All HTTP timeouts are `(connect, read)` tuples** so a slow Snowflake call can't wedge the proxy's circuit breaker.
- **The anchor table uses `CREATE OR REPLACE`** so a schema change can never collide with a stale table left by a prior deploy.
- **Plain ASCII in the transform SQL** — em/en-dashes in comments crash the Snowflake parser.

## Extending it

- **New metrics** are just new SQL — no redeploy needed; the agent authors them against the live schema.
- **More source tables** can be added by widening the borrowed role's read scope and extending the `get_metadata` guide text.
- **Lineage:** the federation works through `SQL_EXEC_MCP_SRVR`'s cross-schema visibility; declared `data_product_input(...)` lineage to the two source DPs can be added later for catalog/graph completeness without changing the runtime path.
