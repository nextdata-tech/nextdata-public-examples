"""
__mcp__.py  --  account-coverage data product MCP tools.

Three tools let an AI agent explore per-account coverage / value-gap data that
lives in one Snowflake table (PARTNER_AZ_DB.ACCOUNT_COVERAGE.ACCOUNT_COVERAGE):

  * get_schema      -- returns the table's columns + rich descriptions, read
                       straight from the data product's own semantic model in
                       models.py. ENGINE-AGNOSTIC: no INFORMATION_SCHEMA, no SQL,
                       no hardcoded schema dictionary -- the model IS the source
                       of truth, so it works unchanged on any backing engine.
                       Call this FIRST.
  * execute_query   -- PRIMARY / DEFAULT data tool. Runs an arbitrary read-only
                       SELECT / WITH that the agent authored itself. There are NO
                       canned business queries in this code; the agent builds SQL
                       from get_schema's output. Use for anything expressible with
                       the columns -- including qualitative wording that maps to a
                       column (e.g. "under-served" -> coverage_flag).
  * search_accounts -- NARROW fallback. Natural-language semantic search over the
                       generated account_profile_text column via the
                       ACCOUNT_COVERAGE_SEARCH Cortex Search service. Use ONLY when
                       the request cannot be expressed with the columns (a free-text
                       theme with no column, or "accounts similar to X"). A question
                       is answered with exactly ONE of these two tools, never both.

Nothing about WHERE the data lives is hardcoded: the Snowflake account / user /
warehouse / DATABASE / SCHEMA / credentials all come from the injected
`snowflake` output-port context, the table name comes from the context's
model_tables (falling back to the model's own declared output name), and the
Cortex Search service name is derived from that same database/schema/table.

Why every literal lives INSIDE a function
-----------------------------------------
nxd extracts each tool into its own generated module on the RPC pod, carrying
module-level imports and `def`/`class` statements but NOT module-level constant
assignments. A module-level `FOO = "bar"` referenced inside a tool becomes a
runtime NameError. So every fixed string is a LOCAL inside a function, the shared
Snowflake logic is a module-level `def` (which survives), the model is imported
INSIDE get_schema, and `Response` is re-imported inside each tool body. The
request/response models below stay at module scope on purpose -- they are
consumed at BUILD time by nxd_spec.py, not by the deployed bodies.
"""

from nxd.core.context import Snowflake
from nxd.drivers.rpc import Request
from nxd.drivers.rpc import Response
from nxd.drivers.rpc import function
from nxd.drivers.rpc import mcp
from nxd.spec import semantic_model
from nxd.spec.data_types import string


# ─────────────────────────────────────────────────────────────────────────────
# MCP request / response models (consumed at BUILD time by nxd_spec.py).
# ─────────────────────────────────────────────────────────────────────────────
get_schema_request = semantic_model(
    name="get_schema_request",
    description="Request the account-coverage table schema. Takes no meaningful input.",
).schema(
    {
        "detail": (
            string(),
            "Optional and ignored. Pass null. Present only so the tool accepts a call.",
        ),
    }
)

get_schema_response = semantic_model(
    name="get_schema_response",
    description=(
        "Account-coverage table schema, read from the data product's own semantic "
        "model in models.py (engine-agnostic, not from any storage engine): column "
        "names, types, descriptions, plus routing guidance."
    ),
).schema(
    {
        "schema": (string(), "Table name, columns with types and descriptions, and query guidance."),
    }
)

execute_query_request = semantic_model(
    name="execute_query_request",
    description="A complete SQL SELECT or WITH statement to run against the account-coverage table (the default/primary tool for these accounts).",
).schema(
    {
        "sql": (
            string(),
            "A complete read-only SQL SELECT or WITH statement against "
            "PARTNER_AZ_DB.ACCOUNT_COVERAGE.ACCOUNT_COVERAGE. Call get_schema first to learn "
            "the columns. Do NOT append a trailing LIMIT -- the server paginates for you.",
        ),
    }
)

execute_query_response = semantic_model(
    name="execute_query_response",
    description="Results of the SQL query as a text table plus a row count.",
).schema(
    {
        "result": (string(), "Query results rendered as a tab-separated text table."),
        "row_count": (string(), "Number of data rows returned, as a string ('NA' if unknown)."),
    }
)

search_accounts_request = semantic_model(
    name="search_accounts_request",
    description="Natural-language semantic search over account profiles via Cortex Search.",
).schema(
    {
        "query": (
            string(),
            "Plain-English description of a free-text profile theme or a similarity target "
            "that has NO structured column, e.g. 'accounts similar to ACCT-00421' or 'profiles "
            "that mention switching to a competitor'. Matched semantically against each "
            "account's generated profile text. Requests that map to columns (specialty, tier, "
            "coverage_flag, engagement, value gap, ...) should use execute_query instead.",
        ),
        "limit": (
            string(),
            "Max results to return as an integer string. Default '10', clamped to 1..50.",
        ),
    }
)

search_accounts_response = semantic_model(
    name="search_accounts_response",
    description="Accounts matching the semantic search, as a text table.",
).schema(
    {
        "result": (string(), "Matching accounts rendered as a tab-separated text table."),
        "count": (string(), "Number of accounts returned, as a string."),
    }
)


# ─────────────────────────────────────────────────────────────────────────────
# Module-level helper (a `def` survives nxd extraction). Opens ONE authenticated
# Snowflake SQL_EXEC session derived entirely from the injected context and
# returns a `run(sql) -> rendered text` callable. Every fixed string is a LOCAL.
# Shared by get_schema, execute_query and search_accounts.
# ─────────────────────────────────────────────────────────────────────────────
def _snowflake_session(snowflake, client_name):
    import json
    import requests as req

    SQL_EXEC_SERVER = "SQL_EXEC_MCP_SRVR"   # Snowflake-native MCP server name (platform convention)
    SCHEMA_FALLBACK = "ACCOUNT_COVERAGE"    # used ONLY if the DP's own schema hosts no exec server
    T_LOGIN  = (5, 25)
    T_INIT   = (5, 25)
    T_NOTIFY = (5, 10)
    T_CALL   = (5, 110)

    def _extract_text(resp):
        def _from_obj(obj):
            if isinstance(obj, dict) and obj.get("error"):
                err = obj["error"]
                return f"Snowflake error: {err.get('message', err) if isinstance(err, dict) else err}"
            result = obj.get("result", obj) if isinstance(obj, dict) else obj
            if isinstance(result, dict):
                content = result.get("content")
                if isinstance(content, list):
                    parts = [c.get("text", "") for c in content if isinstance(c, dict)]
                    joined = "\n".join(p for p in parts if p)
                    if joined:
                        return joined
                if "structuredContent" in result:
                    return json.dumps(result["structuredContent"])
            return json.dumps(result)

        ctype = (resp.headers.get("Content-Type") or "").lower()
        if "text/event-stream" in ctype:
            texts = []
            for line in resp.text.splitlines():
                line = line.strip()
                if not line.startswith("data:"):
                    continue
                payload = line[len("data:"):].strip()
                if not payload or payload == "[DONE]":
                    continue
                try:
                    texts.append(_from_obj(json.loads(payload)))
                except Exception:
                    texts.append(payload)
            return "\n".join(t for t in texts if t) or resp.text
        try:
            return _from_obj(resp.json())
        except Exception:
            return resp.text

    def _render_result(text):
        if not isinstance(text, str) or not text.lstrip().startswith("{"):
            return text
        try:
            obj = json.loads(text)
        except Exception:
            return text
        rs = obj.get("result_set") if isinstance(obj, dict) else None
        if not isinstance(rs, dict):
            return text
        data = rs.get("data") or []
        meta = rs.get("resultSetMetaData") or {}
        rowtype = meta.get("rowType") or []
        cols = [c.get("name", f"col{i}") for i, c in enumerate(rowtype)]
        lines = []
        if cols:
            lines.append("\t".join(cols))
        for row in data:
            if isinstance(row, list):
                lines.append("\t".join("" if v is None else str(v) for v in row))
            else:
                lines.append(str(row))
        rendered = "\n".join(lines)
        return rendered if rendered.strip() else text

    # --- everything below is DERIVED from the injected context ---------------
    account   = str(snowflake.account).replace("_", "-").lower()
    database  = snowflake.database
    schema    = snowflake.schema
    warehouse = snowflake.warehouse
    base_url  = f"https://{account}.snowflakecomputing.com"

    # 1. login once (account-level) -> session token
    login_resp = req.post(
        f"{base_url}/session/v1/login-request",
        params={"warehouse": warehouse, "databaseName": database, "schemaName": schema},
        json={"data": {"LOGIN_NAME": snowflake.user, "PASSWORD": snowflake.password}},
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        timeout=T_LOGIN,
    )
    login_resp.raise_for_status()
    login_data = login_resp.json()
    if not login_data.get("success"):
        msg = (login_data.get("data", {}) or {}).get("message") or "login rejected"
        raise RuntimeError(f"Snowflake login failed: {msg}")
    token = login_data["data"]["token"]
    base_headers = {
        "Authorization": f'Snowflake Token="{token}"',
        "Content-Type":  "application/json",
        "Accept":        "application/json, text/event-stream",
    }

    # 2. find a usable SQL-exec server: the DP's OWN schema first, then fallback
    exec_schemas = [schema]
    if SCHEMA_FALLBACK and SCHEMA_FALLBACK != schema:
        exec_schemas.append(SCHEMA_FALLBACK)

    mcp_url = None
    headers = None
    last = None
    for exec_schema in exec_schemas:
        candidate = (
            f"{base_url}/api/v2/databases/{database}"
            f"/schemas/{exec_schema}/mcp-servers/{SQL_EXEC_SERVER}"
        )
        try:
            init_resp = req.post(
                candidate,
                json={
                    "jsonrpc": "2.0", "id": "1", "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities":    {"tools": {}},
                        "clientInfo":      {"name": client_name, "version": "1.0.0"},
                    },
                },
                headers=dict(base_headers),
                timeout=T_INIT,
            )
            if init_resp.status_code < 400:
                headers = dict(base_headers)
                sid = init_resp.headers.get("Mcp-Session-Id", "")
                if sid:
                    headers["Mcp-Session-Id"] = sid
                mcp_url = candidate
                req.post(
                    mcp_url,
                    json={"jsonrpc": "2.0", "method": "notifications/initialized"},
                    headers=headers, timeout=T_NOTIFY,
                )
                break
            last = f"schema {exec_schema}: initialize HTTP {init_resp.status_code}"
        except Exception as e:
            last = f"schema {exec_schema}: {type(e).__name__}: {e}"
    if mcp_url is None:
        raise RuntimeError(f"no usable {SQL_EXEC_SERVER} (tried {exec_schemas}); last: {last}")

    state = {"id": 1}

    def run(sql):
        state["id"] += 1
        call_resp = req.post(
            mcp_url,
            json={
                "jsonrpc": "2.0", "id": str(state["id"]), "method": "tools/call",
                "params": {"name": "sql_exec_tool", "arguments": {"sql": sql}},
            },
            headers=headers, timeout=T_CALL,
        )
        call_resp.raise_for_status()
        return _render_result(_extract_text(call_resp))

    return run


# Module-level helper: resolve the fully-qualified table name from context.
def _table_fqn(snowflake):
    database = snowflake.database
    schema = snowflake.schema
    table = "ACCOUNT_COVERAGE"
    try:
        table = (getattr(snowflake, "model_tables", {}) or {}).get("account_coverage", "ACCOUNT_COVERAGE")
    except Exception:
        pass
    return database, schema, table, f"{database}.{schema}.{table}"


# ─────────────────────────────────────────────────────────────────────────────
# Module-level helpers (a `def` survives nxd's per-function pod extraction).
# Read the columns + descriptions from the data product's OWN semantic model
# object -- the single, ENGINE-AGNOSTIC source of truth defined in models.py.
# No INFORMATION_SCHEMA, no SQL, no hardcoded schema dictionary, so the exact
# same code works whether the product is backed by Snowflake, Databricks, or
# anything else. The reader is deliberately exhaustive because nxd's `.schema()`
# builder may keep the columns in the public serialization OR in a Pydantic
# private attribute that model_dump() omits.
#
# IMPORTANT (nxd extraction): when nxd lifts a tool onto the RPC pod it pulls in
# the module-level helpers the TOOL references directly, but it does NOT recurse
# into those helpers' own references. So every sub-helper the reader needs is
# NESTED INSIDE _read_model_columns -- that way it travels with the function and
# cannot become a `name '...' is not defined` NameError on the pod.
# ─────────────────────────────────────────────────────────────────────────────
def _read_model_columns(model):
    def _type_label(dt):
        # A column's data_type may arrive as a plain label ("string"/"int64"), as
        # the platform's decimal form ({"decimal128": {"precision": p, "scale": s}}),
        # or as a live nxd type object. Render any of them to a readable string.
        if dt is None:
            return ""
        if isinstance(dt, str):
            return dt
        if isinstance(dt, dict):
            for _, v in dt.items():
                if isinstance(v, dict) and "precision" in v:
                    return f"decimal({v.get('precision')},{v.get('scale')})"
            ks = list(dt.keys())
            return ks[0] if ks else "object"
        # live type object: prefer its own serialization, then precision/scale, then name
        for meth in ("model_dump", "dict"):
            fn = getattr(dt, meth, None)
            if callable(fn):
                try:
                    out = fn()
                    if isinstance(out, (str, dict)):
                        return _type_label(out)
                except Exception:
                    pass
        p = getattr(dt, "precision", None)
        s = getattr(dt, "scale", None)
        if p is not None and s is not None:
            return f"decimal({p},{s})"
        return getattr(dt, "__name__", None) or type(dt).__name__

    def _norm_attr(item, key=None):
        # Normalize one column entry to (name, type_label, description). The entry
        # may be a dict, an attribute object, or a (type, description) tuple whose
        # name is the mapping key.
        if isinstance(item, tuple):
            t = item[0] if len(item) > 0 else None
            d = item[1] if len(item) > 1 else ""
            return (str(key or ""), _type_label(t), str(d or ""))
        if isinstance(item, dict):
            nm = item.get("name", key) or key or ""
            t = item.get("data_type", item.get("dataType", item.get("type")))
            d = item.get("description", item.get("desc", item.get("comment", "")))
            return (str(nm or ""), _type_label(t), str(d or ""))
        nm = getattr(item, "name", key) or key or ""
        t = getattr(item, "data_type", getattr(item, "dataType", getattr(item, "type", None)))
        d = getattr(item, "description", getattr(item, "desc", ""))
        return (str(nm or ""), _type_label(t), str(d or ""))

    def _columns_from(coll):
        # Turn a dict / list / iterable of column entries into [(name, type, desc), ...].
        if coll is None:
            return []
        out = []
        if isinstance(coll, dict):
            for k, v in coll.items():
                nm, t, d = _norm_attr(v, key=k)
                if nm:
                    out.append((nm, t, d))
            return out
        if isinstance(coll, (list, tuple, set)):
            items = list(coll)
        elif hasattr(coll, "__iter__") and not isinstance(coll, (str, bytes)):
            try:
                items = list(coll)
            except Exception:
                items = []
        else:
            return []
        for v in items:
            nm, t, d = _norm_attr(v)
            if nm:
                out.append((nm, t, d))
        return out

    keys = ("attributes", "fields", "columns", "schema", "attrs")
    # 1) public serialization (Pydantic model_dump / dict)
    for meth in ("model_dump", "dict"):
        fn = getattr(model, meth, None)
        if callable(fn):
            try:
                dumped = fn()
            except Exception:
                dumped = None
            if isinstance(dumped, dict):
                for k in keys:
                    cols = _columns_from(dumped.get(k))
                    if cols:
                        return cols
    # 2) public attributes on the object
    for k in keys:
        cols = _columns_from(getattr(model, k, None))
        if cols:
            return cols
    # 3) Pydantic private attrs + raw __dict__ (the builder may stash them here)
    bags = []
    priv = getattr(model, "__pydantic_private__", None)
    if isinstance(priv, dict):
        bags.append(priv)
    raw = getattr(model, "__dict__", None)
    if isinstance(raw, dict):
        bags.append(raw)
    private_keys = ("_attributes", "attributes", "_fields", "fields",
                    "_columns", "columns", "_schema", "schema", "_attrs", "attrs")
    for bag in bags:
        for k in private_keys:
            if k in bag:
                cols = _columns_from(bag[k])
                if cols:
                    return cols
    # last-ditch: scan the bags for a collection that really looks like columns
    # (several entries, most carrying a description -- avoids grabbing links etc.)
    for bag in bags:
        for v in bag.values():
            cols = _columns_from(v)
            if len(cols) >= 2 and sum(1 for c in cols if c[2]) >= max(2, len(cols) // 2):
                return cols
    return []


def _read_model_description(model):
    for meth in ("model_dump", "dict"):
        fn = getattr(model, meth, None)
        if callable(fn):
            try:
                dumped = fn()
                if isinstance(dumped, dict) and isinstance(dumped.get("description"), str):
                    return dumped["description"]
            except Exception:
                pass
    d = getattr(model, "description", "")
    return d if isinstance(d, str) else ""


# ─────────────────────────────────────────────────────────────────────────────
# Tool 1 -- get_schema  (metadata read from the model in models.py)
# ─────────────────────────────────────────────────────────────────────────────
@function(name="get_schema")
@mcp.tool(
    name="get_schema",
    description=(
        "Returns the account-coverage table's columns, data types, and rich descriptions "
        "(allowed values, business rules, ranking hints) read from the data product's own "
        "semantic model in models.py (engine-agnostic), plus a decision rule for choosing "
        "EXACTLY ONE of execute_query (the default) or search_accounts. ALWAYS call this "
        "first, then author your own SQL for execute_query."
    ),
)
def get_schema(snowflake: Snowflake, request: Request) -> Response:
    import json
    import logging
    from nxd.drivers.rpc import Response

    log = logging.getLogger("mcp.get_schema")
    if not log.handlers:
        log.addHandler(logging.StreamHandler())
    log.setLevel(logging.INFO)
    log.info("=== ENTERED get_schema ===")

    # --- read columns from the data product's OWN semantic model --------------
    # ENGINE-AGNOSTIC on purpose: the schema comes straight from the semantic
    # model defined in models.py (the single source of truth), NOT from any
    # storage engine. No INFORMATION_SCHEMA query, no SQL, no hardcoded schema
    # dictionary -- so this exact tool keeps working unchanged if the product is
    # later backed by Databricks (or anything else) instead of Snowflake.
    from models import account_coverage

    model_desc = _read_model_description(account_coverage)
    cols = _read_model_columns(account_coverage)

    if not cols:
        # Never fail opaquely: report the model object's real shape so the reader
        # can be pointed at the right field in a single step.
        diag = {"type": str(type(account_coverage))}
        try:
            md = getattr(account_coverage, "model_dump", None)
            diag["model_dump_keys"] = sorted((md() or {}).keys()) if callable(md) else "no model_dump"
        except Exception as e:
            diag["model_dump_error"] = str(e)
        diag["public_attrs"] = sorted(a for a in dir(account_coverage) if not a.startswith("__"))[:60]
        diag["dict_keys"] = sorted((getattr(account_coverage, "__dict__", {}) or {}).keys())
        priv = getattr(account_coverage, "__pydantic_private__", None)
        if isinstance(priv, dict):
            diag["private_keys"] = sorted(priv.keys())
        log.error(f"get_schema could not read model columns: {diag}")
        return Response({
            "schema": (
                "ERROR: could not read columns from the account_coverage model object. "
                "DIAGNOSTIC (please share this so the reader can be pinned): "
                + json.dumps(diag)
            )
        })

    # Where to run execute_query. Derived from the injected context so it adapts
    # to whatever engine backs the product -- this is a location hint, NOT schema
    # metadata (the columns/types/descriptions above all come from the model).
    _, _, _, table_fqn = _table_fqn(snowflake)

    lines = []
    lines.append(f"TABLE: {table_fqn}")
    if model_desc:
        lines.append(model_desc)
    lines.append("")
    lines.append("COLUMNS (name, type, description -- read from the semantic model in models.py):")
    search_col = None
    for name, dtype, desc in cols:
        type_part = f" [{dtype}]" if dtype else ""
        lines.append(f"  - {name}{type_part}: {desc}")
        nm = name.lower()
        ds = desc.lower()
        if ("cortex search" in ds or "search index" in ds or "search document" in ds
                or "semantic search" in ds or "profile_text" in nm):
            search_col = name

    guide = []
    guide.append("")
    guide.append("--- HOW TO ANSWER (choose EXACTLY ONE tool) ---")
    guide.append(
        "DEFAULT to execute_query. Use search_accounts only as a narrow fallback. Never "
        "call both tools for the same question."
    )
    guide.append(
        "Decision rule: if EVERY part of the request maps to a column above -- even when "
        "phrased qualitatively -- author SQL and use execute_query. Use search_accounts ONLY "
        "when the request targets a free-text theme in account_profile_text that has no "
        "column, or asks for accounts 'similar to' a given account."
    )
    guide.append(
        "Qualitative wording maps to columns: 'cardiology' -> specialty; "
        "'under-/over-/well-served' -> coverage_flag; 'high/medium/low value' -> "
        "account_value_tier; 'weak/low/strong engagement' -> avg_engagement_score; 'biggest "
        "opportunity / most upside' -> value_gap_usd; 'poorly realized' -> realization_ratio; "
        "'few/many touches' -> touch_count; 'positive response rate' -> positive_rate; segment "
        "A-D -> segment; territory / exclude marketing -> territory_id."
    )
    guide.append("")
    guide.append(
        "execute_query (SQL) -- the default. Author a complete read-only SELECT or WITH "
        f"against {table_fqn} using the columns above. Read-only; do not add a trailing LIMIT "
        "(the server paginates)."
    )
    guide.append("Questions that are SQL (one execute_query each):")
    guide.append(
        "  * 'Cardiology accounts that look under-served with weak engagement' -> WHERE "
        "specialty='Cardiology' AND coverage_flag='Under-served high-value' ORDER BY "
        "avg_engagement_score ASC.  (every term maps to a column -> SQL, NOT search)"
    )
    guide.append(
        "  * 'Top 10 accounts by value gap, excluding the marketing territory' -> WHERE "
        "territory_id <> 'T-MKT' ORDER BY value_gap_usd DESC."
    )
    guide.append("  * 'Average realization ratio by segment' -> GROUP BY segment.")
    guide.append(
        "  * 'How many high-value accounts are under-served?' -> COUNT(*) WHERE "
        "account_value_tier='High' AND coverage_flag='Under-served high-value'."
    )
    guide.append("")
    guide.append(
        "search_accounts (Cortex Search) -- narrow fallback. Pass plain English, NOT SQL. Use "
        "only when no column captures the request."
    )
    guide.append("Questions that are search (one search_accounts each):")
    guide.append("  * 'Accounts similar to ACCT-00421'  (similarity, no column).")
    guide.append(
        "  * 'Accounts whose profile mentions consolidating purchasing into a GPO'  (a theme "
        "with no column)."
    )
    guide.append("  * 'Find accounts described as price-sensitive'  (narrative, no column).")
    if search_col:
        guide.append(
            f"Column '{search_col}' is the semantic-search text used by search_accounts. It is "
            "NOT a filterable SQL column -- never put it in a WHERE clause."
        )
    guide.append("")
    guide.append(
        "Mixed request (a column filter PLUS a free-text theme with no column, e.g. 'cardiology "
        "accounts whose profile mentions budget pressure'): still answer with ONE tool. Pick "
        "the dominant intent -- usually execute_query for the structured filter -- or, to "
        "combine both in a single statement, call SNOWFLAKE.CORTEX.SEARCH_PREVIEW INSIDE your "
        "execute_query SQL. Do not fire both tools."
    )
    guide.append("")
    guide.append("SQL tips (build these yourself; illustrations, not canned queries):")
    guide.append("  * Rank by upside: ORDER BY value_gap_usd DESC.")
    guide.append("  * Field-rep analysis: WHERE territory_id <> 'T-MKT' (exclude marketing).")
    guide.append(
        "  * Percentages: ROUND(realization_ratio * 100, 1) and ROUND(positive_rate * 100, 1)."
    )
    guide.append(
        "  * Coverage mix: GROUP BY coverage_flag; filter under-served accounts with "
        "coverage_flag = 'Under-served high-value'."
    )

    log.info("=== get_schema RETURNING OK ===")
    return Response({"schema": "\n".join(lines + guide)})


# ─────────────────────────────────────────────────────────────────────────────
# Tool 2 -- execute_query  (runs the agent's own read-only SQL)
# ─────────────────────────────────────────────────────────────────────────────
@function(name="execute_query")
@mcp.tool(
    name="execute_query",
    description=(
        "PRIMARY / DEFAULT tool for questions about these accounts. Executes a single "
        "read-only SQL SELECT or WITH that YOU author against "
        "PARTNER_AZ_DB.ACCOUNT_COVERAGE.ACCOUNT_COVERAGE for any filter, aggregation, "
        "ranking, or count. Use this whenever the request can be expressed with the "
        "get_schema columns -- INCLUDING qualitative wording that maps to a column, e.g. "
        "'cardiology' -> specialty, 'under-served' -> coverage_flag, 'high-value' -> "
        "account_value_tier, 'weak/low engagement' -> avg_engagement_score, 'biggest "
        "opportunity' -> value_gap_usd. Call get_schema first. Do not append a trailing "
        "LIMIT. Answer with exactly ONE tool: only use search_accounts when NO column can "
        "express the request, and never call both tools for the same question."
    ),
)
def execute_query(snowflake: Snowflake, request: Request) -> Response:
    import logging
    import re
    from nxd.drivers.rpc import Response

    log = logging.getLogger("mcp.execute_query")
    if not log.handlers:
        log.addHandler(logging.StreamHandler())
    log.setLevel(logging.INFO)
    log.info("=== ENTERED execute_query ===")

    sql = request.get("sql") or ""
    sql = sql.strip().rstrip(";").strip() if isinstance(sql, str) else ""
    if not sql:
        return Response({"result": "ERROR: no SQL provided (expected a 'sql' argument).", "row_count": "0"})

    low = sql.lower()
    if not (low.startswith("select") or low.startswith("with")):
        return Response({"result": "ERROR: only read-only SELECT or WITH statements are allowed.", "row_count": "0"})
    if ";" in low:
        return Response({"result": "ERROR: statement is not a single read-only query (found ';').", "row_count": "0"})
    forbidden = (" insert ", " update ", " delete ", " drop ", " alter ", " create ",
                 " merge ", " truncate ", " grant ", " revoke ", " call ")
    padded = f" {low} "
    hit = next((tok.strip() for tok in forbidden if tok in padded), None)
    if hit:
        return Response({"result": f"ERROR: statement is not a single read-only query (found '{hit}').", "row_count": "0"})

    # Strip a trailing LIMIT n -- the Snowflake MCP server appends its own.
    sql = re.sub(r"\s+limit\s+\d+\s*$", "", sql, flags=re.IGNORECASE).strip()

    try:
        run = _snowflake_session(snowflake, client_name="account-coverage-execute-query")
        result_text = run(sql)
    except Exception as e:
        log.error(f"execute_query failed: {e}")
        return Response({"result": f"ERROR executing query: {e}", "row_count": "0"})

    row_count = "NA"
    try:
        non_empty = [ln for ln in result_text.splitlines() if ln.strip()]
        if len(non_empty) > 1:
            row_count = str(max(len(non_empty) - 1, 0))
    except Exception:
        pass

    log.info("=== execute_query RETURNING OK ===")
    return Response({"result": result_text, "row_count": row_count})


# ─────────────────────────────────────────────────────────────────────────────
# Tool 3 -- search_accounts  (Cortex Search semantic similarity)
# ─────────────────────────────────────────────────────────────────────────────
@function(name="search_accounts")
@mcp.tool(
    name="search_accounts",
    description=(
        "NARROW fallback tool. Semantic free-text search over each account's natural-language "
        "profile (account_profile_text) via the ACCOUNT_COVERAGE_SEARCH Cortex Search service. "
        "Use ONLY when the request CANNOT be expressed as a filter on the get_schema columns -- "
        "e.g. similarity ('accounts similar to ACCT-00421') or a theme that lives only in the "
        "profile narrative and has no column ('profiles that mention consolidating purchasing', "
        "'accounts described as price-sensitive'). Do NOT use this for requests that map to "
        "columns even when phrased loosely -- specialty, account_value_tier, segment, "
        "territory_id, coverage_flag, or any numeric threshold (engagement, value gap, "
        "realization, touches) all belong to execute_query. Pass plain English in 'query' (NOT "
        "SQL). Answer with exactly ONE tool: never call this alongside execute_query for the "
        "same question."
    ),
)
def search_accounts(snowflake: Snowflake, request: Request) -> Response:
    import json
    import logging
    from nxd.drivers.rpc import Response

    log = logging.getLogger("mcp.search_accounts")
    if not log.handlers:
        log.addHandler(logging.StreamHandler())
    log.setLevel(logging.INFO)
    log.info("=== ENTERED search_accounts ===")

    query = request.get("query") or ""
    query = query.strip() if isinstance(query, str) else ""
    if not query:
        return Response({"result": "ERROR: no search query provided (expected a 'query' argument).", "count": "0"})

    try:
        limit = int(str(request.get("limit") or "10").strip())
    except Exception:
        limit = 10
    limit = max(1, min(limit, 50))

    # Cortex Search service name derives from the same db/schema/table as the data,
    # following the '<table>_SEARCH' convention used when the service was created.
    database, schema, table, _ = _table_fqn(snowflake)
    service_fqn = f"{database}.{schema}.{table}_SEARCH"

    # Columns to return for each hit. These are structured attributes of the search
    # service (the profile text itself is the match target, not a returned column).
    display_cols = [
        "account_id", "account_value_tier", "segment", "specialty",
        "territory_id", "coverage_flag", "value_gap_usd",
    ]

    search_payload = json.dumps({"query": query, "columns": display_cols, "limit": limit})
    payload_sql = search_payload.replace("'", "''")   # escape for the SQL string literal
    search_sql = (
        f"SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW('{service_fqn}', '{payload_sql}') AS search_result"
    )

    try:
        run = _snowflake_session(snowflake, client_name="account-coverage-search-accounts")
        rendered = run(search_sql)
    except Exception as e:
        log.error(f"search_accounts failed: {e}")
        return Response({"result": f"ERROR running Cortex Search: {e}", "count": "0"})

    # SEARCH_PREVIEW returns a single cell containing a JSON string:
    # {"results": [ {col: val, ...}, ... ], "request_id": "..."}.
    # run() renders that as "SEARCH_RESULT\n<json>"; take the JSON and parse it.
    try:
        cell_lines = [ln for ln in rendered.splitlines() if ln.strip()]
        payload = cell_lines[-1] if len(cell_lines) >= 2 else rendered
        parsed = json.loads(payload)
        results = parsed.get("results", []) if isinstance(parsed, dict) else []
    except Exception as e:
        log.error(f"could not parse Cortex Search response: {e}")
        return Response({"result": rendered, "count": "NA"})

    if not results:
        return Response({"result": f"No accounts matched: {query}", "count": "0"})

    # Render the hits as a tab-separated table, columns in our requested order
    # (plus any extra keys the service returned, for safety).
    ordered = [c for c in display_cols if c in results[0]]
    extras = [c for c in results[0].keys() if c not in ordered]
    cols = ordered + extras
    out = ["\t".join(cols)]
    for r in results:
        out.append("\t".join("" if r.get(c) is None else str(r.get(c)) for c in cols))

    log.info("=== search_accounts RETURNING OK ===")
    return Response({"result": "\n".join(out), "count": str(len(results))})