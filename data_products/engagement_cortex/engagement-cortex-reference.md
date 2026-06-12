# engagement-cortex: implementation reference

One MCP tool. Natural-language questions in, answers + the SQL Cortex Analyst wrote, out. Everything lives in Snowflake; the data product pod is just an authenticated bridge.

---

## 1. What this is

`engagement-cortex` is an NXD data product whose only purpose is to expose a single MCP tool named `ask`. An AI agent (Claude Desktop, or any MCP client) sends a natural-language question about pharmaceutical commercial engagement analytics; the tool returns four fields: a narrative `answer`, the `sql` Cortex Analyst authored, the executed result as a tab-separated `data` table, and a `row_count`.

The agent never sees a schema and never writes SQL. There is no `get_schema` tool on purpose. All translation from question to SQL happens inside Snowflake using Cortex Agent + Cortex Analyst, driven by a YAML semantic model.

The data underneath comes from an upstream `engagement-analytics` data product. `engagement-cortex` reads two tables from it: `CHANNEL_EFFECTIVENESS` (per-channel effectiveness and cost-efficiency) and `MONTHLY_TRENDS` (monthly activity and the F2F-to-digital channel shift).

---

## 2. Architecture

```
Claude Desktop  (natural language only)
        |
        v
NXD MCP proxy
        |
        v
engagement-cortex RPC pod   <-- __mcp__.py 'ask' tool lives here
        |  Snowflake REST + JSON-RPC MCP handshake
        v
Snowflake MCP server: ENGAGEMENT_CORTEX_MCP_SRVR
        |  built-in tool: type = CORTEX_AGENT_RUN
        v
Cortex Agent: ENGAGEMENT_ANALYST_AGENT
        |  tool: cortex_analyst_text_to_sql
        |  tool_resources.execution_environment.warehouse = PARTNER_AZ_WH
        v
Cortex Analyst  (uses engagement_analytics.yaml semantic model)
        |  generates AND executes SQL
        v
Warehouse: PARTNER_AZ_WH
        |
        v
Tables: PARTNER_AZ_DB.ENGAGEMENT_ANALYTICS.{CHANNEL_EFFECTIVENESS, MONTHLY_TRENDS}
```

Why this design rather than the more common pattern (let the agent fetch a schema, author SQL, hand it to a SQL executor)?

Two reasons. First, the agent's SQL is unverified and may drift across runs; Cortex Analyst's SQL is governed by a versioned YAML semantic model and benefits from verified-query pinning. Second, the agent never sees customer data shapes, column names, or PII column hints — those live behind Snowflake's auth boundary throughout the call.

---

## 3. Implementation

### 3.1 File layout

```
engagement_cortex/
  __mcp__.py                          one file, three module-level functions
  spec.py                             data product spec (DP API + RPC port)
  models.py                           cortex_registry anchor model
  nxd_models.py                       semantic_model + string imports
  nxd_spec.py                         re-exports for the single-import rule
  requirements.txt                    nxd-core, nxd-drivers[rpc], requests
  transform/
    build_cortex_registry.sql         creates the anchor table on launch
```

Plus a separate deployment kit (one-time Snowflake setup):

```
deployment/
  01_schema_and_stage.sql             schema + SEMANTIC_MODELS stage
  02_upload_semantic_model.sh         PUT engagement_analytics.yaml to stage
  03_create_agent.sql                 CREATE AGENT + DATA_AGENT_RUN smoke test
  04_create_mcp_server.sql            CREATE MCP SERVER with ask_engagement tool
  05_grants.sql                       grants to PARTNER_AZ_ROLE
semantic_model/
  engagement_analytics.yaml           the source of truth for NL-to-SQL
```

### 3.2 The three module-level functions in __mcp__.py

NXD's deployment model extracts each MCP tool function plus its referenced module-level helpers into its own pod (`/app/__ask__.py` on the running pod, not `__mcp__.py` — the platform renames per tool). Module-level constants do NOT survive this extraction; only `def`s and imports do. This drives several patterns below.

**`ask(snowflake, request) -> Response`** — the tool entry point. Decorated with `@mcp.tool` and a semantic-model binding that declares the input/output schema. Body:

1. Validate the question is non-empty
2. Log the question length and a preview under the `[ASK]` sentinel
3. Build `arguments = {"text": question}` — flat top-level text parameter (not a `messages` envelope; the MCP server wraps internally)
4. Call `_call_cortex_mcp` inside `try/except`; on exception, return a `Response` whose `answer` field contains the exception type, message, and full traceback
5. Call `_parse_agent_response` inside a separate `try/except`; on exception, return a `Response` with traceback + a 1000-character head of the raw response
6. On success, return `Response({"answer": ..., "sql": ..., "data": ..., "row_count": ...})`

The two `try/except` wrappers are the guarantee that the framework never surfaces an opaque "Tool execution failed" — whatever goes wrong is captured in the `answer` field as text.

**`_call_cortex_mcp(snowflake, tool_name, arguments, client_name) -> str`** — the Snowflake driver. All constants live inside the function because of the extraction-model constraint: `MCP_DATABASE`, `MCP_SCHEMA`, `MCP_SERVER` for the target, and a quartet of `(connect, read)` timeout tuples (`T_LOGIN`, `T_INIT`, `T_NOTIFY`, `T_CALL`). The `T_CALL` read timeout is 180 seconds because Cortex Agent first-calls can take 30-60 seconds end-to-end (warehouse cold start + analyst inference + SQL execution); shorter calls might hit the timeout before the agent responds.

Five HTTP calls happen here. The first authenticates against Snowflake to get a session token. The next four are JSON-RPC against the MCP server URL: `initialize`, `tools/list` (discovery, non-fatal), `notifications/initialized` (fire-and-forget), and finally `tools/call`. Every call is timed and logged under `[CX]`; HTTP errors capture status code + body head + latency before the exception propagates.

A nested helper `_extract_text(resp)` normalizes responses regardless of `Content-Type`. JSON-RPC bodies are unwrapped to their `result` envelope and serialized back to JSON string. `text/event-stream` (SSE) bodies have their `data: ` prefixes stripped and the payloads concatenated. Either way, the output is a string that `_parse_agent_response` can walk.

**`_parse_agent_response(raw_text) -> dict`** — extracts four flat string fields from a rich nested response. The Cortex Agent response is multi-part: a `thinking` block, a `tool_use` block (containing the SQL the analyst is about to run), a `tool_results` block (containing the executed `result_set`), a `text` block (the narrative answer), a `table` block, and a `suggested_queries` block.

The parser walks the structure recursively, looking for three things:

- `tool_use.input.sql` → captured as the SQL
- `tool_results.content[].json.result_set` (with variants `resultSet`, `data_result`, `rows`) → captured as the executed data
- `text` blocks → captured as the narrative answer

It explicitly skips `tool_use` blocks during text-extraction recursion, otherwise the original question would leak into the answer. Rows are rendered as a tab-separated text table with column headers from `resultSetMetaData.rowType`.

### 3.3 NXD extraction model constraints

These dictate the implementation more than anything else:

- Module-level bare constants do not survive extraction → every constant lives inside the function that uses it
- Helper functions must be reachable from the tool function → all three helpers are module-level `def`s
- Nested helpers are fine and recommended → `_extract_text` and `_walk` (inside the parser) are nested
- Imports at the function level are fine and used liberally (`import logging`, `import time`, `import requests as req`, `import traceback`)
- Files in the upload must have LF line endings and no non-ASCII bytes — Snowflake's SQL parser has crashed on CRLF and on em-dashes in prior incidents
- The semantic-model binding (`ask_request`, `ask_response`) is the one exception to "no module-level state" — it's a build-time binding, not runtime state

### 3.4 Instrumentation

Two sentinel markers in logs make diagnosis fast:

- `[CX]` on every line emitted by `_call_cortex_mcp` (HTTP boundary tracing)
- `[ASK]` on every line emitted by `ask` (tool-level state)

For each HTTP call, the log line captures the status code, latency in milliseconds, and (on error) up to 1000 characters of the response body head. The `tools/list` discovery call logs the schema the server actually advertises, which is the ground truth for what `arguments` shape the next `tools/call` expects.

Both helper invocations in `ask` are inside `try/except`. On any exception, the `answer` field of the returned `Response` contains:

- The exception type and message
- A full Python traceback
- (For parser failures) a 1000-character head of the raw response that caused the crash

This means a failed call always returns actionable detail to whoever invoked the tool, and the same detail also lands in the pod logs.

---

## 4. The semantic model

`engagement_analytics.yaml` is the source of truth Cortex Analyst reads to translate questions into SQL. It declares two logical tables, their dimensions and measures (with synonyms), and seven verified queries that act as gold-standard NL-to-SQL examples.

### 4.1 channel_effectiveness — one row per channel

Maps to `PARTNER_AZ_DB.ENGAGEMENT_ANALYTICS.CHANNEL_EFFECTIVENESS`. Primary key is `channel`.

Dimension: `channel` (text). Sample values: F2F, Remote, Email, Phone, Conference, Virtual Event.

Measures:

| measure | aggregation | description |
|---|---|---|
| `activity_count` | sum | Number of activities on the channel |
| `avg_engagement_score` | avg | Mean engagement quality, 0-100 |
| `positive_rate` | avg | Share of activities with positive response, 0-1 |
| `on_preferred_channel_rate` | avg | Share aligned with account's preferred channel, 0-1 |
| `total_cost_usd` | sum | Fully-loaded cost, USD |
| `cost_per_positive_usd` | avg | Cost divided by positive responses |

### 4.2 monthly_trends — one row per calendar month

Maps to `PARTNER_AZ_DB.ENGAGEMENT_ANALYTICS.MONTHLY_TRENDS`. Primary key is `activity_month` (text, YYYY-MM).

Time dimension: `activity_month`. Sample values: 2025-01, 2025-06, 2025-12.

Measures:

| measure | aggregation | description |
|---|---|---|
| `activity_count` | sum | Activities in the month |
| `avg_engagement_score` | avg | Mean engagement, 0-100 |
| `positive_rate` | avg | Monthly positive response share, 0-1 |
| `f2f_share` | avg | Share of activities on F2F channel, 0-1 |
| `digital_share` | avg | Share on Email/Remote/Virtual Event, 0-1 |
| `total_cost_usd` | sum | Total monthly cost, USD |

### 4.3 Verified queries

The YAML pins seven verified question/SQL pairs. When Cortex Analyst recognises a question as matching one of these, it executes the pinned SQL directly without re-authoring. This is the "fast path" — typically under 2 seconds wall-clock once the warehouse is warm.

The seven verified questions are:

1. *Which channel is the most cost-efficient (lowest cost per positive response)?*
2. *Which channel has the highest positive response rate?*
3. *Rank channels by average engagement score.*
4. *What is the F2F-to-digital shift over time?*
5. *How has the positive response rate trended month over month?*
6. *Which channel had the highest total spend?*
7. *Summarise the latest month: volume, engagement, positive rate, and channel mix.*

Verified-query SQL uses logical table names (`__channel_effectiveness`, `__monthly_trends`) which Cortex Analyst wraps into CTEs against the physical tables at execution time.

---

## 5. Lifecycle of a query

The phases below trace one user question from Claude Desktop down to the warehouse and back, with timings for a warm path (verified-query match, warehouse running).

### Phase 1: Reception (10-50 ms)

Claude Desktop holds an established MCP session with the `engagement-cortex-demo__mcp-api` connector. The user types a question. Claude composes:

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "ask",
    "arguments": {"question": "Which channel has the highest positive response rate?"}
  }
}
```

…and sends it to the NXD proxy. The proxy validates auth, consults its circuit breaker (closed = pass through, open = fail fast with a generic error), and forwards the call over HTTP to the data product pod.

### Phase 2: Pod entry (1-5 ms)

The framework dispatches the `tools/call` to the `ask` function. First log line:

```
mcp.ask|INFO|[ASK] === ENTERED ask ===
mcp.ask|INFO|[ASK] question_len=52 preview='Which channel has the highest positive response rate?'
```

`ask` validates the question is non-empty, builds `arguments = {"text": question}`, and calls `_call_cortex_mcp`.

### Phase 3: The five HTTP calls to Snowflake (varies; dominated by call 5)

All five POSTs go to `https://<account>.snowflakecomputing.com`. Each one logs status, latency, and (on error) body head.

| Call | Endpoint | Purpose | Typical latency |
|---|---|---|---|
| 1 | `/session/v1/login-request` | Exchange user/password for session token | 200-400 ms |
| 2 | `/api/v2/.../mcp-servers/.../`  method=`initialize` | MCP capability handshake; capture `Mcp-Session-Id` header | 300-600 ms |
| 3 | same URL, method=`tools/list` | Discovery — log the tool's input schema (non-fatal if it fails) | 200-400 ms |
| 4 | same URL, method=`notifications/initialized` | Protocol courtesy step; fire-and-forget | 100-200 ms |
| 5 | same URL, method=`tools/call`, name=`ask_engagement` | THE call — agent runs here | 1-60 seconds |

The body of call 5 is:

```json
{
  "jsonrpc": "2.0",
  "id": "2",
  "method": "tools/call",
  "params": {
    "name": "ask_engagement",
    "arguments": {"text": "Which channel has the highest positive response rate?"}
  }
}
```

The Snowflake MCP server validates that `text` is non-empty (a missing or empty `text` returns a 400 with `"Text parameter is required and cannot be empty"`), then forwards to the Cortex Agent.

### Phase 4: Inside Snowflake (1-60 seconds — varies by warmth and verified-query match)

`ENGAGEMENT_CORTEX_MCP_SRVR` (created in deployment step 04 with one tool `ask_engagement` of type `CORTEX_AGENT_RUN`) wraps the text into the agent's required `messages` envelope and invokes `ENGAGEMENT_ANALYST_AGENT`.

The agent has one tool configured: `cortex_analyst_text_to_sql`, pointing at the YAML semantic model at `@PARTNER_AZ_DB.ENGAGEMENT_CORTEX.SEMANTIC_MODELS/engagement_analytics.yaml`. Its `execution_environment.warehouse` is set to `PARTNER_AZ_WH`, which is what lets Cortex Analyst not just *generate* SQL but also *execute* it.

The agent's planner picks the analyst tool, hands it the question, and waits. Cortex Analyst does one of two things:

- **Verified-query path**: if the question fuzzy-matches one of the seven pinned questions in the YAML, it executes the pinned SQL directly. Total time ~1-2 seconds on a warm warehouse.
- **Composition path**: otherwise it uses the LLM to compose new SQL from the dimensions, measures, and synonyms in the semantic model. Total time ~5-30 seconds.

In both cases, the SQL runs on `PARTNER_AZ_WH` against the physical tables under `PARTNER_AZ_DB.ENGAGEMENT_ANALYTICS`. The rows come back to the agent, which composes a narrative answer using both the SQL and the data, then returns a structured response with all of it: `thinking`, `tool_use` (the SQL chosen), `tool_results` (the executed result_set), `text` (the narrative), `table`, `suggested_queries`.

### Phase 5: Response unwrap (5-20 ms)

`_call_cortex_mcp` logs:

```
[CX] call status=200 latency_ms=1842 content_type='application/json' body_len=5234
[CX] call body_head='{"content": [{"thinking": {"text": "..."}, "type": "thinking"}, ...'
[CX] extracted_len=4823 extracted_head='{"content": [...]}'
```

`_extract_text` returns the result envelope as a JSON string. `_parse_agent_response` walks the structure, captures the SQL and result_set, renders rows as TSV, and returns the four-field dictionary:

```
[ASK] _call_cortex_mcp returned raw_len=4823
[ASK] parsed sql_present=yes rows=6 answer_len=287
[ASK] === ask RETURNING OK ===
```

The `Response` object travels back through the proxy to Claude Desktop, which renders the `answer` to the user.

### Phase 6: Total wall-clock

| Scenario | Time |
|---|---|
| Warm warehouse + verified-query match | 1-2 s |
| Warm warehouse + composed SQL | 5-15 s |
| Cold warehouse + verified-query match | 10-30 s |
| Cold warehouse + composed SQL + complex aggregation | 30-90 s |

---

## 6. Sample questions

### 6.1 Verified-query fast path

These match the seven pinned queries in the YAML and exercise the verified-query path:

- *Which channel has the highest positive response rate?*
- *Rank channels by average engagement score.*
- *Which channel is the most cost-efficient?*
- *Which channel had the highest total spend?*
- *What is the F2F-to-digital shift over time?*
- *How has the positive response rate trended month over month?*
- *Summarise the latest month.*

### 6.2 Novel questions (Cortex Analyst composes new SQL)

These are NOT in the verified-query list. The agent must use the YAML's dimensions, measures, and synonyms to compose SQL from scratch. They're good demo material because they show Cortex Analyst doing real work rather than replaying a fixture.

Channel-level questions:

- *Which channel has the lowest activity volume?*
- *What is the total spend across all channels?*
- *Compare F2F and Email on engagement quality and cost.*
- *Which channels exceed 50 activities?*
- *Which channel has the worst alignment with the account's preferred channel?*
- *How much was spent on channels with an average engagement score below 50?*
- *What is the cost per positive response on the digital channels (Email, Remote, Virtual Event)?*
- *What percentage of total spend went to F2F?*
- *Which channels cost more than $1000 per positive response?*

Monthly-trend questions:

- *What was the engagement score in June 2025?*
- *How many activities happened in the first half of 2025?*
- *Show months where the positive response rate fell below 40 percent.*
- *What was the average monthly spend across 2025?*
- *Compare engagement quality between January 2025 and December 2025.*
- *In which month was digital share at its highest?*
- *What is the trend in monthly activity volume?*
- *Has digital share grown by more than 20 percentage points year over year?*

Cross-cutting / synthesis questions:

- *Summarise channel mix and engagement quality for the most recent three months.*
- *Which channels were responsible for the rising digital share?*
- *Was the months-with-highest-engagement also months-with-highest-spend?*

### 6.3 Edge cases (the model should decline)

These are out of scope for the semantic model (dimensions or facts that don't exist). A well-tuned agent should respond with a clarification rather than hallucinate.

- *Which sales rep has the highest engagement?* (no rep dimension)
- *Show me revenue by product.* (no revenue or product dimensions)
- *Forecast next quarter's spend.* (no forecasting capability)
- *What's the engagement score for account XYZ?* (no account-level grain)

These are also useful as demo material — they show the guard-rails working.

---

## 7. Observability

### 7.1 Pod-side logs (real-time)

Pull with the NXD partner MCP tool:

```
proxy__getDataProductLogs(data_product='engagement-cortex-demo', debug=true)
```

Grep for `[CX]` to see HTTP-boundary traces (login, init, list, notify, call status codes + latency + body heads). Grep for `[ASK]` to see tool-level state (entry, return, exceptions). Anchor a failure trace by finding `[ASK] === ENTERED ask ===` and reading forward.

### 7.2 Snowflake-side traces (AI_OBSERVABILITY_EVENTS)

Cortex Agents emit traces automatically to `SNOWFLAKE.LOCAL.AI_OBSERVABILITY_EVENTS`. No event-table setup, no `TRACE_LEVEL` parameter, no account-admin involvement to *enable* — it's on by default.

To see *metadata only* (span structure, latencies, token usage, tool names), the role only needs `MONITOR` on the agent:

```sql
SELECT *
FROM TABLE(SNOWFLAKE.LOCAL.GET_AI_OBSERVABILITY_EVENTS(
    'PARTNER_AZ_DB',
    'ENGAGEMENT_CORTEX',
    'ENGAGEMENT_ANALYST_AGENT',
    'CORTEX AGENT'
))
WHERE OBSERVED_TIMESTAMP > DATEADD(hour, -1, CURRENT_TIMESTAMP())
ORDER BY OBSERVED_TIMESTAMP DESC;
```

To see *unredacted content* (the actual NL question and generated SQL text), an account admin must grant once:

```sql
GRANT READ UNREDACTED AI OBSERVABILITY EVENTS TABLE ON ACCOUNT
    TO ROLE PARTNER_AZ_ROLE;
```

After that the query above returns full attribute text. The Snowsight UI at AI & ML → Agents → ENGAGEMENT_ANALYST_AGENT → Monitoring shows the same data in a friendlier form.

### 7.3 QUERY_HISTORY correlation

Whatever Cortex Analyst executes against `PARTNER_AZ_WH` shows up in `QUERY_HISTORY`. This is useful for joining agent traces to actual query cost and execution stats:

```sql
SELECT START_TIME, USER_NAME, TOTAL_ELAPSED_TIME, ROWS_PRODUCED, QUERY_TEXT
FROM   SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE  WAREHOUSE_NAME = 'PARTNER_AZ_WH'
  AND  START_TIME >= DATEADD(hour, -1, CURRENT_TIMESTAMP())
  AND  (QUERY_TEXT ILIKE '%CHANNEL_EFFECTIVENESS%'
     OR QUERY_TEXT ILIKE '%MONTHLY_TRENDS%')
ORDER BY START_TIME DESC;
```

---

## 8. Known failure modes

| Symptom | Where logged | Cause | Fix |
|---|---|---|---|
| `[CX] login HTTP error: 401` | pod | Wrong creds or expired password | Rotate creds at platform |
| `[CX] init HTTP error: 401/403` | pod | Auth header rejected by MCP server | Verify session-token auth is accepted; PAT/OAuth may be required |
| `[CX] init HTTP error: 404` | pod | MCP server name or path wrong | Verify ENGAGEMENT_CORTEX_MCP_SRVR exists |
| `[CX] call HTTP 400 "Text parameter is required"` | pod | Wrong `arguments` shape | Send `{"text": question}`, not `messages` envelope |
| `[CX] call HTTP 500` | pod | Cortex internal error | Inspect body head; usually transient |
| `[CX] call transport error after ~180000 ms` | pod | Tools/call timeout | Investigate why agent is slow (cold warehouse? complex composition?) |
| `[ASK] _parse_agent_response raised:` | pod | Response shape we don't yet handle | Add a branch in `_parse_agent_response._walk` for the new node type |
| Claude shows answer but with `sql=""` | pod | `_extract_text` discarded structured content | Confirm `_from_obj` returns full result envelope (not just text blocks) |
| Tool call succeeds at proxy but Claude shows "Tool execution failed" | proxy + pod | Pod returned non-MCP-compliant Response | Check `[ASK] === ask RETURNING OK ===` is present in logs |

---

## 9. Deployment quick reference

Initial Snowflake setup (one-time, done by an admin):

```bash
# In a Snowflake worksheet, as ACCOUNTADMIN or equivalent:
\i deployment/01_schema_and_stage.sql
bash deployment/02_upload_semantic_model.sh
\i deployment/03_create_agent.sql
\i deployment/04_create_mcp_server.sql
\i deployment/05_grants.sql
```

Data product deploy:

```bash
nxd undeploy --skip-version-check --url $NXD_BASE_URL/api engagement-cortex-demo
nxd launch  --skip-version-check --skip-status-polling --debug-mode --url $NXD_BASE_URL/api 2>&1 | tee launch.log
```

Health check after launch:

```
proxy__getDataProductsHealth(filter_broken_only=false)
```

Expected steady state: `engagement-cortex-demo__mcp-api` → derived_state=Healthy, mcp.breaker.state=Closed, mcp.tool_count=1.

Trigger one query from Claude Desktop, then pull logs:

```
proxy__getDataProductLogs(data_product='engagement-cortex-demo', debug=true)
```

Look for `[ASK] === ask RETURNING OK ===` to confirm end-to-end success.

---

## Appendix: file inventory

```
engagement_cortex/__mcp__.py                          MCP tool entry point + helpers
engagement_cortex/spec.py                             data product spec
engagement_cortex/models.py                           cortex_registry anchor
engagement_cortex/nxd_models.py                       nxd imports
engagement_cortex/nxd_spec.py                         nxd imports
engagement_cortex/requirements.txt                    Python deps
engagement_cortex/transform/build_cortex_registry.sql first-launch transform
semantic_model/engagement_analytics.yaml              the source of truth for NL-to-SQL
deployment/01_schema_and_stage.sql                    Snowflake schema + stage
deployment/02_upload_semantic_model.sh                stage upload script
deployment/03_create_agent.sql                        CREATE AGENT + smoke test
deployment/04_create_mcp_server.sql                   CREATE MCP SERVER
deployment/05_grants.sql                              role grants
test_questions.md                                     curated NL queries for testing
```
