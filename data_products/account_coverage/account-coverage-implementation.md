# account-coverage — Implementation Guide

A practical walkthrough of how the `account-coverage` data product is built and how it answers questions. Written so a developer who has never seen this code can read it top-to-bottom and know **what each file does** and **what calls what**.

---

## 1. What this product is, in one paragraph

`account-coverage` takes a raw CRM activity feed and turns it into **one row per account** describing how well each account is being covered by the sales force: how much revenue is realised vs. possible, how many times reps touched it, what it cost, and a plain-English verdict like *"Under-served high-value"*. That table lives in Snowflake. On top of it sit **three tools** that an AI agent (Claude Desktop) can call over MCP: one to read the schema, one to run SQL, and one to do natural-language search. The agent uses these tools to answer business questions without ever seeing raw tables directly.

There are two separate jobs going on, and it helps to keep them apart in your head:

- **Build the table** (the *data plane*) — a scheduled SQL job. Runs occasionally.
- **Answer questions** (the *serve plane*) — the three tools. Runs every time the agent asks something.

---

## 2. The big picture

```
SERVE PLANE  —  real time: answer a question
─────────────────────────────────────────────
   AI agent (Claude Desktop)
        │   MCP: tools/call
        ▼
   nxd-partner proxy
        │
        ▼
   account-coverage  ·  "mcp-api" port  (tool runs in a pod)
        │
        ├─ get_schema ──────────► reads models.py IN-PROCESS   (no Snowflake call)
        │
        ├─ execute_query ───┐
        │                   ├─ _snowflake_session(...).run(sql)
        ├─ search_accounts ─┘     (search first builds a SEARCH_PREVIEW SQL string)
        │                         │
        ▼                         ▼
   Snowflake:  PARTNER_AZ_DB.ACCOUNT_COVERAGE
        ├─ ACCOUNT_COVERAGE          (the table, 15 columns)
        └─ ACCOUNT_COVERAGE_SEARCH   (Cortex Search over account_profile_text)


DATA PLANE  —  scheduled: build the table
─────────────────────────────────────────
   crm-activity product
        ├─ account  table
        └─ activity table
        │   read by
        ▼
   transform.sql   (runs on Snowflake compute)
        │   TRUNCATE + INSERT
        ▼
   ACCOUNT_COVERAGE table  ──►  automatically re-indexed by ACCOUNT_COVERAGE_SEARCH
```

The single most important thing to notice: **`get_schema` never touches Snowflake.** It reads the column list from the Python model object in `models.py`. The other two tools *do* go to Snowflake, and they both go through one shared helper, `_snowflake_session`.

---

## 3. The files, and what each one is for

The product is seven files. Five are Python, one is SQL, one is a dependency list.

| File | What it does | Who uses it |
|------|--------------|-------------|
| `__mcp__.py` | **The runtime brain.** Defines the 3 tools, the helpers they share, and the request/response shapes. Everything that happens when the agent calls a tool happens here. | nxd loads each tool onto a pod at runtime |
| `models.py` | **The schema, as the source of truth.** Defines `account_coverage` (the 15-column output) plus `account` and `activity` (what we expect from the upstream input). | `get_schema` reads it; `spec.py` references it |
| `nxd_models.py` | Re-exports the model/type building blocks (`string`, `int64`, `decimal`, `semantic_model`, …) so `models.py` has one clean import line. | imported by `models.py` |
| `nxd_spec.py` | A single "import surface". Re-exports the 3 tools, their request/response models, the 3 data models, and the nxd spec primitives — so `spec.py` can do one `import *`. | imported by `spec.py` |
| `spec.py` | **The wiring diagram.** Declares the data product: its name, the transform, the one input, and the two outputs (the Snowflake table + the MCP tool endpoint). nxd reads this to deploy. | read by nxd at deploy time |
| `transform.sql` | **The build logic.** Pure SQL that reads crm-activity and writes the `ACCOUNT_COVERAGE` table (including the text that search indexes). | run by nxd on Snowflake |
| `requirements.txt` | One line: `requests==2.31.0`. Used by `_snowflake_session` to make HTTP calls. | the tool pods |

### How the files import each other (build time)

```
spec.py
  └── import *  from  nxd_spec.py
                        ├── imports 3 tools + request/response models  from  __mcp__.py
                        ├── imports account / activity / account_coverage  from  models.py
                        │                                                          └── import * from nxd_models.py
                        └── imports nxd.spec primitives (data_product, sql, storage, rpc_server, …)
```

So `spec.py` is the top of the tree. Reading it tells you the whole shape of the product. `__mcp__.py` and `models.py` are the leaves that hold the actual logic and schema.

---

## 4. The data model (what a row looks like)

Every row is one account. These 15 columns are defined in `models.py` and are exactly what `get_schema` reports back to the agent.

| Column | Type | Meaning |
|--------|------|---------|
| `account_id` | string | Unique account id. Joins back to crm-activity. |
| `account_value_tier` | string | `High` / `Medium` / `Low`. |
| `segment` | string | Field-force segment `A`–`D` (A = top priority). |
| `specialty` | string | Medical specialty (Cardiology, Oncology, …). |
| `territory_id` | string | Sales territory. **Exclude `'T-MKT'`** (marketing) from rep analysis. |
| `potential_value_usd` | int64 | Revenue opportunity if fully realised. |
| `actual_value_usd` | int64 | Revenue actually realised. |
| `value_gap_usd` | int64 | `potential − actual`. Bigger = more upside. **Use this to rank.** |
| `realization_ratio` | decimal(6,4) | `actual / potential`, 0–1. |
| `touch_count` | int64 | How many field activities were logged. |
| `total_cost_usd` | int64 | What those activities cost. |
| `avg_engagement_score` | decimal(6,2) | Average engagement quality, 0–100. |
| `positive_rate` | decimal(6,4) | Fraction of activities with a positive response, 0–1. |
| `coverage_flag` | string | The verdict (see below). |
| `account_profile_text` | string | A generated sentence describing the account. **This is what search reads. Never put it in a `WHERE` clause.** |

**`coverage_flag`** is the opinionated bit. The transform computes it with simple rules:

- `Under-served high-value` — high tier, realising < 25% of potential, touched ≤ 2 times. *(The accounts worth chasing.)*
- `Well-served high-value` — high tier, touched ≥ 3 times, every touch got a positive response.
- `Over-served low-value` — low tier, but getting expensive face-to-face visits with negative/no responses.
- `Adequate` — everything else.

---

## 5. The three tools (this is the "what calls what")

All three live in `__mcp__.py`. Each one is a function `tool(snowflake, request) -> Response`. Here is exactly what each does and what it calls.

### 5.1 `get_schema` — "tell me the columns"

**Calls:** `_read_model_description`, `_read_model_columns`, `_table_fqn`. **Hits Snowflake:** no.

What happens, step by step:

1. Imports the `account_coverage` model object from `models.py` (in-process — it's just a Python object).
2. Calls `_read_model_description(account_coverage)` → the table's description text.
3. Calls `_read_model_columns(account_coverage)` → a list of `(name, type, description)` for all 15 columns.
4. Calls `_table_fqn(snowflake)` → the fully-qualified table name, used **only** as a label to show the agent where the data lives (not to read metadata).
5. Builds a text block: the column list **plus a routing guide** that tells the agent how to pick between `execute_query` and `search_accounts`.
6. Returns `{"schema": "<that text>"}`.

```python
def get_schema(snowflake, request):
    from models import account_coverage           # the source of truth
    desc = _read_model_description(account_coverage)
    cols = _read_model_columns(account_coverage)   # [(name, type, description), ...]
    _, _, _, table_fqn = _table_fqn(snowflake)     # label only
    # ... format `cols` + append the "choose exactly one tool" guide ...
    return Response({"schema": text})
```

Why read the model instead of asking Snowflake? See §7.2 — it keeps the product engine-agnostic.

### 5.2 `execute_query` — "run this SQL"

**Calls:** `_snowflake_session`. **Hits Snowflake:** yes. This is the **default** tool.

What happens:

1. Reads `request["sql"]`.
2. **Safety guard** (all rejected with no DB call): must start with `SELECT` or `WITH`; no `;`; no `INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/MERGE/TRUNCATE/GRANT/REVOKE/CALL`.
3. Strips any trailing `LIMIT n` — the Snowflake server adds its own pagination.
4. Calls `_snowflake_session(snowflake, client_name="...")`, which returns a `run(sql)` function.
5. Calls `run(sql)` → gets the result back as a tab-separated table.
6. Returns `{"result": "<table>", "row_count": "<n>"}`.

```python
def execute_query(snowflake, request):
    sql = (request.get("sql") or "").strip().rstrip(";")
    # guard: SELECT/WITH only, single statement, no DDL/DML  -> else return an ERROR Response
    sql = re.sub(r"\s+limit\s+\d+\s*$", "", sql, flags=re.I)   # server paginates
    run = _snowflake_session(snowflake, client_name="account-coverage-execute-query")
    return Response({"result": run(sql), "row_count": ...})
```

The agent writes the SQL itself (using the columns from `get_schema`). There are **no canned queries** hidden in the code.

### 5.3 `search_accounts` — "find accounts that read like…"

**Calls:** `_table_fqn`, `_snowflake_session`. **Hits Snowflake:** yes (Cortex Search). This is the **narrow fallback** tool.

What happens:

1. Reads `request["query"]` (plain English) and `limit` (clamped to 1–50).
2. Calls `_table_fqn(snowflake)` → `(database, schema, table)`, then builds the search-service name by convention: `<database>.<schema>.<table>_SEARCH`.
3. Builds a SQL string that calls Cortex Search:
   `SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW('<service>', '<json payload>')`
   where the payload is `{"query": ..., "columns": [...], "limit": ...}`.
4. Calls `_snowflake_session(...).run(search_sql)` — same helper as `execute_query`.
5. The result is a single JSON cell; it parses the `results` array out of it.
6. Returns `{"result": "<table>", "count": "<n>"}`.

```python
def search_accounts(snowflake, request):
    database, schema, table, _ = _table_fqn(snowflake)
    service_fqn = f"{database}.{schema}.{table}_SEARCH"
    payload = json.dumps({"query": query, "columns": display_cols, "limit": limit})
    search_sql = f"SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW('{service_fqn}', '{payload}')"
    run = _snowflake_session(snowflake, client_name="account-coverage-search-accounts")
    rendered = run(search_sql)   # one JSON cell -> parse "results"
    return Response({"result": ..., "count": ...})
```

So `search_accounts` is really just "build a special SQL string, then run it through the same session helper." It is **not** a separate connection path.

---

## 6. The shared helpers (the plumbing the tools call)

These are module-level functions in `__mcp__.py`. The tools call them; you rarely change them.

### 6.1 `_snowflake_session(snowflake, client_name)` → returns `run(sql)`

This is the only thing that actually talks to Snowflake. It logs in once and hands back a `run` function you call as many times as you like. Both `execute_query` and `search_accounts` use it.

The connection is Snowflake's native **SQL-exec MCP server** (`SQL_EXEC_MCP_SRVR`), reached over HTTP. The handshake is a fixed 3-step sequence, then you can call the tool:

```
1. login          POST /session/v1/login-request          -> session token
                  (sends warehouse + database + schema + user + password)

2. initialize     POST .../mcp-servers/SQL_EXEC_MCP_SRVR    (jsonrpc "initialize")
   ready          POST .../notifications/initialized
                  (tries the DP's OWN schema first; falls back to ACCOUNT_COVERAGE)

3. run(sql)       POST tools/call
                  { "name": "sql_exec_tool", "arguments": { "sql": "<your sql>" } }
                  -> response contains a result_set -> rendered to a TSV table
```

Details worth knowing:

- Everything (account, database, schema, warehouse, user, password) comes from the injected `snowflake` context object. **Nothing about *where* the data lives is hardcoded.**
- The argument key the server expects is exactly `"sql"`.
- Timeouts are `(connect, read)` tuples — the read timeout is generous because queries can be slow.
- It has nested helpers (`_extract_text`, `_render_result`, `_from_obj`, and `run` itself). They are nested **on purpose** — see §7.1.

### 6.2 `_table_fqn(snowflake)` → `(database, schema, table, "db.schema.table")`

Tiny helper. Pulls `database` and `schema` from the context, gets the table name from `snowflake.model_tables["account_coverage"]` (falling back to the literal `ACCOUNT_COVERAGE`), and returns all four. Used by `get_schema` (for a label) and `search_accounts` (to build the search-service name).

### 6.3 `_read_model_columns(model)` → `[(name, type, description), ...]`

Reads the 15 columns out of the `account_coverage` Python model object. It looks more complicated than you'd expect, for two real reasons:

- The nxd model builder sometimes stores the columns in a **public** place and sometimes in a **private** Pydantic attribute that `model_dump()` hides. So the reader tries several strategies in order — public serialization, then public attributes, then private attributes / raw `__dict__` — and takes the first that yields columns.
- A column's type can arrive as a plain string (`"string"`), as a dict (`{"decimal128": {"precision": 6, "scale": 4}}`), or as a live type object. A nested helper `_type_label` turns any of those into a readable label like `decimal(6,4)`.

It has three nested helpers: `_type_label`, `_norm_attr`, `_columns_from`. They are nested **on purpose** (§7.1). If it ever fails to find columns, `get_schema` returns a diagnostic dump of the model object instead of a vague error, so you can fix the accessor in one shot.

### 6.4 `_read_model_description(model)` → string

Same idea, simpler: pulls the model's description text, trying a couple of accessors.

---

## 7. Why the code looks the way it does (decisions + the bugs behind them)

These four points explain choices that otherwise look odd. Each came from a real failure.

### 7.1 Helpers are nested, and there are no module-level constants

**The rule:** when nxd deploys the MCP port, it lifts **each tool into its own isolated module on a pod**. That lift is shallow:

- It carries the tool function and the module-level `def`s the tool references **directly**.
- It does **not** follow references *inside* those helpers, and it **drops module-level constant assignments** (a top-level `NAME = "x"`).

So two things will bite you if you forget:

1. A top-level constant used inside a tool becomes a `NameError` on the pod. **Fix:** keep fixed strings as locals inside the function.
2. A helper that calls *another* helper breaks, because the second one isn't carried. This actually happened: `get_schema` → `_read_model_columns` (carried) → `_columns_from` (**dropped**) → `name '_columns_from' is not defined`. **Fix:** nest a helper's sub-helpers *inside* it, so they travel together. That's why `_read_model_columns` and `_snowflake_session` contain their helpers as inner functions.

### 7.2 The schema comes from `models.py`, not from Snowflake

`get_schema` could have run `SELECT … FROM INFORMATION_SCHEMA`. It deliberately doesn't. Reading the Python model means the schema is **engine-agnostic** — if this product were re-pointed at Databricks tomorrow, `get_schema` would not change. The model is the single source of truth; the warehouse is just where the rows happen to sit. (The cost is the careful reader in §6.3, because the model object stores its columns in an awkward place.)

### 7.3 One question → exactly one tool

`execute_query` and `search_accounts` are separate tools, so the agent could call both for one question — and it did, for *"Cardiology accounts that look under-served with weak engagement"*. That question is actually pure SQL (every word maps to a column). The tool **descriptions** are written to prevent this:

- `execute_query` is marked the **default**, and lists qualitative phrases that map to columns (`"under-served"` → `coverage_flag`, `"weak engagement"` → `avg_engagement_score`, …).
- `search_accounts` is marked a **narrow fallback** — only for things no column can express (a theme in the profile text, or "accounts similar to X") — with an explicit "never call alongside `execute_query`".
- `get_schema`'s output repeats this as a short decision rule with worked examples.

This is guidance the agent follows, not a hard lock. A hard guarantee would need a single combined tool. (See §9 for which questions go where.)

### 7.4 Snowflake gotchas baked into the code

- **ASCII only in SQL strings.** A Unicode em-dash or smart quote crashes the Snowflake parser. (Box-drawing characters are fine in Python *comments* — that's UTF-8 source, not SQL.)
- **Read-only guard** on every SQL tool: `SELECT`/`WITH` only, single statement, no DDL/DML.
- **Strip trailing `LIMIT`** — the native server paginates, so a user `LIMIT` is removed before sending.

---

## 8. The transform (how the table gets built)

`transform.sql` runs on Snowflake compute, on nxd's schedule. In order:

1. Reads the two upstream tables from the **crm-activity** product (`account` and `activity`) via Jinja input placeholders.
2. Aggregates `activity` per account: `touch_count`, `total_cost_usd`, average engagement, positive-response count, face-to-face count, etc.
3. Joins that back to `account` and computes the derived fields: `value_gap_usd`, `realization_ratio`, `positive_rate`, and the `coverage_flag` rules from §4.
4. Builds `account_profile_text` — one sentence folding the structured fields into prose (this is what Cortex Search indexes).
5. Writes with **`TRUNCATE` then `INSERT`** into the nxd-managed `ACCOUNT_COVERAGE` table.

Why `TRUNCATE`+`INSERT` and not `DROP`+`CREATE`? Because the `ACCOUNT_COVERAGE_SEARCH` Cortex Search service is attached to that table object. Dropping the table would break the service. Truncate-and-reload keeps the table (and the service) alive and just refreshes the rows.

> Note: an earlier version did this work in a Snowpark stored procedure and failed with *"this session does not have a current schema."* The transform session has no default schema, so everything must be **fully-qualified**. That's why it's plain qualified SQL now.

---

## 9. Worked examples — which tool runs, and what it calls

Concrete end-to-end traces. This is the fastest way to internalise the routing.

**"Top 10 accounts by value gap, excluding the marketing territory"**
→ `execute_query` (every term maps to a column)
→ guard passes → `_snowflake_session().run("SELECT … WHERE territory_id <> 'T-MKT' ORDER BY value_gap_usd DESC")`
→ Snowflake returns rows → TSV back to the agent.

**"How many high-value accounts are under-served?"**
→ `execute_query`
→ `run("SELECT COUNT(*) … WHERE account_value_tier='High' AND coverage_flag='Under-served high-value'")`.

**"What columns are available?" / agent's first step**
→ `get_schema`
→ reads `models.py` in-process, formats 15 columns + the routing guide → returns text. **No Snowflake call.**

**"Accounts whose profile mentions consolidating purchasing into a GPO"**
→ `search_accounts` (no column holds this idea)
→ builds `SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW('PARTNER_AZ_DB.ACCOUNT_COVERAGE.ACCOUNT_COVERAGE_SEARCH', '{…}')`
→ `_snowflake_session().run(that sql)` → parse JSON `results` → table back.

**"Accounts similar to ACCT-00421"**
→ `search_accounts` (similarity, not a filter).

**The tricky one: "Cardiology accounts whose profile mentions budget pressure"**
→ one filter that's a column (`specialty`) + one idea that isn't (`budget pressure`). The contract says **pick one tool**: usually `execute_query` for the structured part, or push the search into a single SQL via `SEARCH_PREVIEW`. It does **not** fire both tools.

---

## 10. Running, testing, deploying

- **Tests (offline).** The real nxd package isn't importable in a sandbox, so the test suite runs the tools against small nxd stubs (fake `Snowflake` context + a fake `requests` that scripts the login→initialize→tools/call handshake). 98 checks cover: the schema reader across several model shapes, the read-only guard (forbidden statements rejected with no network), `LIMIT` stripping, the Cortex Search payload, the routing descriptions, and a **faithful pod-extraction test** that rebuilds each tool the way nxd does (tool + only its directly-referenced helpers) so a missing nested helper would fail the test, not production.
- **Deploy.** nxd reads `spec.py`. After deploying, restart Claude Desktop and make one tool call so the freshly deployed tool registers (discovery lags a deploy by a short window).
- **When a tool misbehaves.** Use the proxy's health check first; it's authoritative. The pod's `logging`/stdout shows framework-level logs — which is why `get_schema` carries its own in-band diagnostic for the one case (schema read) where a Python traceback might not surface.

---

## 11. Thirty-second summary

- **`__mcp__.py`** holds the 3 tools + shared helpers. **`models.py`** is the schema. **`spec.py`** wires it together. **`transform.sql`** builds the table.
- **`get_schema`** reads the schema from `models.py` — no Snowflake.
- **`execute_query`** (default) and **`search_accounts`** (fallback) both go to Snowflake through **`_snowflake_session`**; search just builds a `SEARCH_PREVIEW` SQL first.
- Helpers are **nested** and there are **no module constants**, because nxd lifts each tool onto a pod shallowly.
- The agent picks **exactly one** tool per question; the tool descriptions enforce it.
