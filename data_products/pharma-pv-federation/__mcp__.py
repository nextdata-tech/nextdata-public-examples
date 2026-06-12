"""
__mcp__.py  --  pharma-pv-federation orchestrator MCP tools.

Two MCP tools let an AI agent run cross-domain pharmacovigilance queries over
two independently-governed data products that live in Snowflake:

  * get_metadata            -- returns the LIVE schema (column names, data types,
                               comments) of the two federated tables straight from
                               INFORMATION_SCHEMA, plus the join keys and the
                               reporting-rate metric definition. Call this FIRST.

  * execute_federated_query -- runs an arbitrary read-only SELECT / WITH against
                               Snowflake, typically the cross-domain JOIN of
                               adverse_event_summary (Drug Safety) with
                               prescription_volume (Commercial).

Because get_metadata returns the real schema, the agent authors its own SQL and
is NOT limited to a fixed list of questions.

Execution path
--------------
Both tools authenticate with the credentials of THIS data product's own
"snowflake" output port (injected as the `snowflake` context) and then drive
Snowflake's SQL_EXEC_MCP_SRVR under the ACCOUNT_COVERAGE schema -- a proven
execution endpoint whose role can read every schema in PARTNER_AZ_DB:

    login  ->  initialize (capture Mcp-Session-Id)
           ->  notifications/initialized
           ->  tools/call (sql_exec_tool)

IMPORTANT -- why every literal is defined INSIDE a function
-----------------------------------------------------------
nxd extracts each tool function into its own generated module on the RPC pod. It
carries over module-level IMPORTS and module-level `def`/`class` statements (so a
shared helper `def` survives, exactly like configure_logger in the canonical
competitor_growth_analysis example), but it does NOT carry over module-level bare
constant assignments (FOO = "bar"). Any such constant referenced inside a tool
becomes a NameError at runtime ("name 'FED_DB' is not defined"). Therefore:
  * Constants (table names, the borrowed MCP schema, timeouts) are LOCALS inside
    the function/helper that uses them -- never module-level.
  * `Response` is re-imported inside each function body for the same reason.
  * The request/response semantic models below stay at module scope on purpose:
    they are consumed at BUILD time by nxd_spec.py, not by the deployed bodies.
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
# These module-level objects are fine where they are -- the deployed function
# bodies never reference them, so it does not matter that extraction drops them
# from the RPC pod.
# ─────────────────────────────────────────────────────────────────────────────
get_metadata_request = semantic_model(
    name="get_metadata_request",
    description="Request for the live schema of the federated pharmacovigilance tables.",
).schema(
    {
        "database": (
            string(),
            "Optional. Snowflake database to introspect. Defaults to PARTNER_AZ_DB.",
        ),
    }
)

get_metadata_response = semantic_model(
    name="get_metadata_response",
    description="Live schema of the two federated tables plus join/metric guidance.",
).schema(
    {
        "metadata": (string(), "Human-readable schema + join keys + metric formula."),
        "source": (string(), "Where the metadata came from (live INFORMATION_SCHEMA, or error)."),
    }
)

execute_federated_query_request = semantic_model(
    name="execute_federated_query_request",
    description="A single read-only SQL statement (SELECT or WITH) to run in Snowflake.",
).schema(
    {
        "sql": (
            string(),
            "The SQL SELECT/WITH to execute. Use fully-qualified names like "
            "PARTNER_AZ_DB.DRUG_SAFETY_SIGNALS.ADVERSE_EVENT_SUMMARY. Do NOT add a "
            "trailing LIMIT -- the server paginates results itself.",
        ),
    }
)

execute_federated_query_response = semantic_model(
    name="execute_federated_query_response",
    description="Tabular result text from Snowflake plus a status line.",
).schema(
    {
        "result": (string(), "Query result rendered as text (columns + rows)."),
        "row_count": (string(), "Number of rows returned, as a string ('NA' if unknown)."),
    }
)


# ─────────────────────────────────────────────────────────────────────────────
# Module-level helper. A `def` survives nxd's per-function extraction (proven by
# configure_logger in competitor_growth_analysis), so both tools share it. Every
# constant it needs is LOCAL, because module-level bare constants do NOT survive.
# Raises on transport / auth failure; callers convert to a tool-friendly string.
# ─────────────────────────────────────────────────────────────────────────────
def _run_sql_via_snowflake_mcp(snowflake, sql, client_name):
    import json
    import requests as req

    # The Snowflake MCP server we borrow for execution. ACCOUNT_COVERAGE's
    # SQL_EXEC_MCP_SRVR role can see all of PARTNER_AZ_DB, so the cross-schema
    # federated JOIN runs without extra grants.
    MCP_DATABASE = "PARTNER_AZ_DB"
    MCP_SCHEMA   = "ACCOUNT_COVERAGE"
    MCP_SERVER   = "SQL_EXEC_MCP_SRVR"

    # (connect, read) timeouts -- tuples everywhere, so one slow Snowflake call
    # can never blow past the proxy's per-call window and wedge the breaker.
    T_LOGIN  = (5, 25)
    T_INIT   = (5, 25)
    T_NOTIFY = (5, 10)
    T_CALL   = (5, 110)

    def _extract_text(resp):
        """Pull text out of an MCP tools/call response, handling both a single
        JSON-RPC object and an SSE (text/event-stream) body."""
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
        """If `text` is a Snowflake sql_exec_tool result_set JSON, render it as a
        tab-separated table (header + rows). Otherwise return it unchanged, so
        error strings and already-plain text pass through verbatim."""
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

    account   = snowflake.account.replace("_", "-").lower()
    user      = snowflake.user
    password  = snowflake.password
    warehouse = snowflake.warehouse
    database  = snowflake.database
    schema    = snowflake.schema
    base_url  = f"https://{account}.snowflakecomputing.com"

    mcp_url = (
        f"{base_url}/api/v2/databases/{MCP_DATABASE}"
        f"/schemas/{MCP_SCHEMA}"
        f"/mcp-servers/{MCP_SERVER}"
    )

    # -- 1. Login -> session token -------------------------------------------
    login_resp = req.post(
        f"{base_url}/session/v1/login-request",
        params={"warehouse": warehouse, "databaseName": database, "schemaName": schema},
        json={"data": {"LOGIN_NAME": user, "PASSWORD": password}},
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        timeout=T_LOGIN,
    )
    login_resp.raise_for_status()
    login_data = login_resp.json()
    if not login_data.get("success"):
        msg = (login_data.get("data", {}) or {}).get("message") or "login rejected"
        raise RuntimeError(f"Snowflake login failed: {msg}")
    session_token = login_data["data"]["token"]

    mcp_headers = {
        "Authorization": f'Snowflake Token="{session_token}"',
        "Content-Type":  "application/json",
        "Accept":        "application/json, text/event-stream",
    }

    # -- 2. initialize (capture session id) ----------------------------------
    init_resp = req.post(
        mcp_url,
        json={
            "jsonrpc": "2.0", "id": "1", "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities":    {"tools": {}},
                "clientInfo":      {"name": client_name, "version": "1.0.0"},
            },
        },
        headers=dict(mcp_headers),
        timeout=T_INIT,
    )
    init_resp.raise_for_status()
    mcp_sid = init_resp.headers.get("Mcp-Session-Id", "")
    if mcp_sid:
        mcp_headers["Mcp-Session-Id"] = mcp_sid

    # -- 3. notifications/initialized ----------------------------------------
    req.post(
        mcp_url,
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        headers=mcp_headers,
        timeout=T_NOTIFY,
    )

    # -- 4. tools/call -> sql_exec_tool --------------------------------------
    # The Snowflake SQL_EXEC_MCP_SRVR tool expects its argument under the key
    # "sql". Verified against the live server: sending "query" yields
    # "sql request parameter is required and cannot be empty".
    call_resp = req.post(
        mcp_url,
        json={
            "jsonrpc": "2.0", "id": "2", "method": "tools/call",
            "params": {"name": "sql_exec_tool", "arguments": {"sql": sql}},
        },
        headers=mcp_headers,
        timeout=T_CALL,
    )
    call_resp.raise_for_status()

    # -- 5. parse (json OR text/event-stream), then render result_set as table -
    return _render_result(_extract_text(call_resp))


# ─────────────────────────────────────────────────────────────────────────────
# Tool 1 -- get_metadata
# ─────────────────────────────────────────────────────────────────────────────
@function(name="get_metadata")
@mcp.tool(
    name="get_metadata",
    description=(
        "Returns the LIVE schema (column names, data types, and comments) of the "
        "two federated pharmacovigilance tables straight from INFORMATION_SCHEMA, "
        "plus the join keys (product_id, region, report_period) and the reporting-"
        "rate metric (adverse events per 1,000 prescriptions). ALWAYS call this "
        "first, then author your own SQL for execute_federated_query."
    ),
)
def get_metadata(snowflake: Snowflake, request: Request) -> Response:
    import logging
    from nxd.drivers.rpc import Response

    # Constants are LOCAL -- module-level bare constants do not survive extraction.
    FED_DB        = "PARTNER_AZ_DB"
    SAFETY_SCHEMA = "DRUG_SAFETY_SIGNALS"
    SAFETY_TABLE  = "ADVERSE_EVENT_SUMMARY"
    COMM_SCHEMA   = "COMMERCIAL_PRESCRIPTIONS"
    COMM_TABLE    = "PRESCRIPTION_VOLUME"

    log = logging.getLogger("mcp.get_metadata")
    if not log.handlers:
        log.addHandler(logging.StreamHandler())
    log.setLevel(logging.INFO)
    log.info("=== ENTERED get_metadata ===")

    db = request.get("database") or FED_DB
    db = db.strip() if isinstance(db, str) else FED_DB
    db = db or FED_DB

    info_sql = (
        "SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE, COMMENT "
        f"FROM {db}.INFORMATION_SCHEMA.COLUMNS "
        f"WHERE (TABLE_SCHEMA = '{SAFETY_SCHEMA}' AND TABLE_NAME = '{SAFETY_TABLE}') "
        f"   OR (TABLE_SCHEMA = '{COMM_SCHEMA}'   AND TABLE_NAME = '{COMM_TABLE}') "
        "ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION"
    )

    try:
        schema_text = _run_sql_via_snowflake_mcp(
            snowflake, info_sql, client_name="pharma-pv-get-metadata"
        )
    except Exception as e:
        log.error(f"get_metadata failed: {e}")
        return Response({"metadata": f"ERROR retrieving live schema: {e}", "source": "error"})

    guide = (
        "\n\n--- FEDERATION GUIDE ---\n"
        f"Numerator table (Drug Safety):  {FED_DB}.{SAFETY_SCHEMA}.{SAFETY_TABLE}\n"
        f"Denominator table (Commercial): {FED_DB}.{COMM_SCHEMA}.{COMM_TABLE}\n"
        "Join keys: product_id, region, report_period (join on all three).\n"
        "Key metric -- adverse-event reporting rate per 1,000 prescriptions:\n"
        "  1000.0 * SUM(s.adverse_event_count) / NULLIF(SUM(c.total_prescriptions), 0)\n"
        "Notes:\n"
        "  * Use fully-qualified table names exactly as shown above.\n"
        "  * Do NOT append a trailing LIMIT; the server paginates for you.\n"
        "  * Raw event COUNT and rate-per-1k can rank products differently --\n"
        "    that inversion is usually the interesting finding.\n"
    )

    err_markers = ("MCP error", "Snowflake error", "SQL compilation error",
                   "cannot be empty", "Invalid input")
    source = "error (snowflake)" if any(m in (schema_text or "") for m in err_markers) else "INFORMATION_SCHEMA (live)"

    log.info("=== get_metadata RETURNING OK ===")
    return Response({"metadata": schema_text + guide, "source": source})


# ─────────────────────────────────────────────────────────────────────────────
# Tool 2 -- execute_federated_query
# ─────────────────────────────────────────────────────────────────────────────
@function(name="execute_federated_query")
@mcp.tool(
    name="execute_federated_query",
    description=(
        "Executes a single read-only SQL statement (SELECT or WITH) in Snowflake -- "
        "typically the cross-domain JOIN of adverse_event_summary (Drug Safety) with "
        "prescription_volume (Commercial) on product_id, region, report_period to "
        "compute the adverse-event reporting rate per 1,000 prescriptions. Use fully-"
        "qualified names (e.g. PARTNER_AZ_DB.DRUG_SAFETY_SIGNALS.ADVERSE_EVENT_SUMMARY). "
        "Call get_metadata first. Do not append a trailing LIMIT."
    ),
)
def execute_federated_query(snowflake: Snowflake, request: Request) -> Response:
    import logging
    import re
    from nxd.drivers.rpc import Response

    log = logging.getLogger("mcp.execute_federated_query")
    if not log.handlers:
        log.addHandler(logging.StreamHandler())
    log.setLevel(logging.INFO)
    log.info("=== ENTERED execute_federated_query ===")

    sql = request.get("sql") or ""
    sql = sql.strip().rstrip(";").strip() if isinstance(sql, str) else ""
    if not sql:
        return Response({"result": "ERROR: no SQL provided (expected a 'sql' argument).", "row_count": "0"})

    low = sql.lower()
    if not (low.startswith("select") or low.startswith("with")):
        return Response({
            "result": "ERROR: only read-only SELECT or WITH statements are allowed.",
            "row_count": "0",
        })

    # Block multi-statement and any write/DDL/proc keyword.
    forbidden = (" insert ", " update ", " delete ", " drop ", " alter ",
                 " create ", " merge ", " truncate ", " grant ", " revoke ", " call ")
    padded = f" {low} "
    if ";" in low:
        return Response({
            "result": "ERROR: statement is not a single read-only query (found ';').",
            "row_count": "0",
        })
    hit = next((tok.strip() for tok in forbidden if tok in padded), None)
    if hit:
        return Response({
            "result": f"ERROR: statement is not a single read-only query (found '{hit}').",
            "row_count": "0",
        })

    # Strip a trailing LIMIT n -- the Snowflake MCP server appends its own.
    sql = re.sub(r"\s+limit\s+\d+\s*$", "", sql, flags=re.IGNORECASE).strip()

    try:
        result_text = _run_sql_via_snowflake_mcp(
            snowflake, sql, client_name="pharma-pv-execute-federated-query"
        )
    except Exception as e:
        log.error(f"execute_federated_query failed: {e}")
        return Response({"result": f"ERROR executing query: {e}", "row_count": "0"})

    row_count = "NA"
    try:
        non_empty = [ln for ln in result_text.splitlines() if ln.strip()]
        if len(non_empty) > 1:
            row_count = str(max(len(non_empty) - 1, 0))
    except Exception:
        pass

    log.info("=== execute_federated_query RETURNING OK ===")
    return Response({"result": result_text, "row_count": row_count})
