"""
account-coverage MCP tools

Three tools:
  get_schema      -- reads column definitions live from models.py by importing
                     the deployed module and introspecting the account_coverage
                     semantic model object. No separate data file, no Snowflake
                     connection, no hardcoded descriptions. Single source of truth.
  execute_query   -- proxies a SQL SELECT through the Snowflake MCP Server.
  search_accounts -- semantic search over account profiles via Cortex Search.
"""

from nxd.core.context import Snowflake
from nxd.drivers.rpc import Request
from nxd.drivers.rpc import Response
from nxd.drivers.rpc import function
from nxd.drivers.rpc import mcp
from nxd.spec import semantic_model
from nxd.spec.data_types import string


# -- Request / response models ------------------------------------------------

get_schema_request = semantic_model(
    name="get_schema_request",
    description="Request the account coverage table schema.",
).schema({"dummy": (string(), "Pass any value -- not used.")})

get_schema_response = semantic_model(
    name="get_schema_response",
    description=(
        "Account coverage table schema read live from models.py. "
        "Reflects the current deployed semantic model definitions."
    ),
).schema({"schema": (string(), "Column names, types, descriptions, and example SQL.")})

execute_query_request = semantic_model(
    name="execute_query_request",
    description="A SQL SELECT query to run against account coverage data.",
).schema({
    "sql": (
        string(),
        "A complete SQL SELECT or WITH statement against "
        "PARTNER_AZ_DB.ACCOUNT_COVERAGE.ACCOUNT_COVERAGE. "
        "Call get_schema first to learn the column names.",
    ),
})

execute_query_response = semantic_model(
    name="execute_query_response",
    description="Results of the SQL query.",
).schema({
    "result":    (string(), "Query results formatted as a text table."),
    "row_count": (string(), "Number of rows returned."),
})

search_accounts_request = semantic_model(
    name="search_accounts_request",
    description="Natural language search over account profiles via Cortex Search.",
).schema({
    "query": (
        string(),
        "Plain English description of the accounts to find. "
        "Examples: 'cardiology accounts with high value gap and low engagement', "
        "'under-served high-value accounts in territory T-03'.",
    ),
    "limit": (string(), "Max results to return. Integer string, default '10', max '50'."),
})

search_accounts_response = semantic_model(
    name="search_accounts_response",
    description="Accounts matching the search query.",
).schema({
    "result": (string(), "Matching accounts returned by Cortex Search."),
    "count":  (string(), "Number of accounts returned."),
})


# -- Tool 1: get_schema -------------------------------------------------------

@function(name="get_schema")
@mcp.tool(
    name="get_schema",
    description=(
        "Get the complete schema of the ACCOUNT_COVERAGE table: column names, "
        "types, and business definitions. Call this before execute_query to learn "
        "the exact column names. Not needed before search_accounts."
    ),
)
def get_schema(request: Request) -> Response:
    """
    Imports models.py (deployed in the same DP package) and reads the
    account_coverage semantic model's internal schema dict directly.

    This is the single-source-of-truth approach: descriptions live only in
    models.py and flow here automatically on every nxd launch. No separate
    data file, no Snowflake connection, no hardcoded column definitions.

    How it works:
      models.account_coverage._schema is the dict passed to .schema() in
      models.py. Each entry is: "col_name": (type_fn_result, "description").
      The nxd.spec.data_types functions return either a plain string ("string",
      "int64") or a dict ({"decimal128": {"precision": N, "scale": M}}).

    Defensive: if _schema is missing (nxd SDK internal change), returns a
    clear error with instructions rather than crashing silently.
    """
    import logging
    import models
    from nxd.drivers.rpc import Response

    log = logging.getLogger(__name__)
    if not log.handlers:
        log.addHandler(logging.StreamHandler())
    log.setLevel(logging.INFO)
    log.info("=== ENTERED get_schema ===")

    # -- Type formatter -------------------------------------------------------
    # nxd.spec.data_types functions return:
    #   string/int64/etc -> plain string  e.g. "string", "int64"
    #   decimal(p,s)     -> dict          e.g. {"decimal128": {"precision":6,"scale":4}}
    def _fmt_type(t):
        if isinstance(t, str):
            return {
                "string":  "VARCHAR",
                "int64":   "NUMBER",
                "int32":   "NUMBER",
                "float64": "FLOAT",
                "float32": "FLOAT",
                "boolean": "BOOLEAN",
                "bool":    "BOOLEAN",
                "date":    "DATE",
            }.get(t, t.upper())
        if isinstance(t, dict) and "decimal128" in t:
            p = t["decimal128"]["precision"]
            s = t["decimal128"]["scale"]
            return "DECIMAL({},{})".format(p, s)
        # Unknown type object -- use string representation as fallback
        return str(t)

    # -- Read schema from models.py ------------------------------------------
    raw_schema = getattr(models.account_coverage, "_schema", None)

    if raw_schema is None:
        msg = (
            "ERROR: models.account_coverage._schema not found.\n"
            "The nxd.spec.semantic_model SDK may have renamed this internal "
            "attribute. Run: vars(models.account_coverage) to find the correct "
            "name, then update this function accordingly."
        )
        log.error(msg)
        return Response({"schema": msg})

    if not raw_schema:
        msg = "ERROR: models.account_coverage._schema is empty."
        log.error(msg)
        return Response({"schema": msg})

    # -- Format columns -------------------------------------------------------
    col_lines = []
    for col_name, value in raw_schema.items():
        if isinstance(value, tuple) and len(value) >= 2:
            type_val, description = value[0], str(value[1])
        elif isinstance(value, dict):
            type_val    = value.get("data_type", "string")
            description = str(value.get("description", ""))
        else:
            type_val, description = "VARCHAR", str(value)
        col_lines.append(
            "  {:<28} {:<16} {}".format(col_name, _fmt_type(type_val), description)
        )

    schema = """TABLE: PARTNER_AZ_DB.ACCOUNT_COVERAGE.ACCOUNT_COVERAGE
Grain: one row per CRM account.
Schema source: models.py ({n} columns)

COLUMNS:
{cols}

TOOL SELECTION GUIDE:
  search_accounts  -- DEFAULT for any plain-English question about accounts.
                      No SQL needed. Finds accounts by meaning and profile.
  execute_query    -- Use ONLY when you have a complete SQL statement to run.
                      Always call get_schema first to know exact column names.

EXAMPLE SQL (for execute_query only):

-- Under-served accounts ranked by value gap
SELECT account_id, specialty, territory_id, value_gap_usd,
       ROUND(realization_ratio * 100, 1) AS realization_pct
FROM PARTNER_AZ_DB.ACCOUNT_COVERAGE.ACCOUNT_COVERAGE
WHERE coverage_flag = 'Under-served high-value'
ORDER BY value_gap_usd DESC LIMIT 10;

-- Territory performance summary (always exclude T-MKT)
SELECT territory_id, COUNT(DISTINCT account_id) AS accounts,
       SUM(value_gap_usd) AS total_gap,
       ROUND(AVG(realization_ratio) * 100, 1) AS avg_realization_pct
FROM PARTNER_AZ_DB.ACCOUNT_COVERAGE.ACCOUNT_COVERAGE
WHERE territory_id != 'T-MKT'
GROUP BY territory_id ORDER BY total_gap DESC;

-- Coverage classification breakdown
SELECT coverage_flag, COUNT(*) AS accounts, SUM(value_gap_usd) AS total_gap
FROM PARTNER_AZ_DB.ACCOUNT_COVERAGE.ACCOUNT_COVERAGE
GROUP BY coverage_flag ORDER BY total_gap DESC;
""".format(n=len(col_lines), cols="\n".join(col_lines))

    log.info("=== get_schema RETURNING ({} columns from models.py) ===".format(len(col_lines)))
    return Response({"schema": schema})

@function(name="execute_query")
@mcp.tool(
    name="execute_query",
    description=(
        "Execute a SQL SELECT statement you have already written "
        "against PARTNER_AZ_DB.ACCOUNT_COVERAGE.ACCOUNT_COVERAGE. "
        "ONLY use this when you have a complete SQL query ready to run. "
        "Do NOT use this for natural language questions -- use search_accounts instead. "
        "Call get_schema first if you need column names."
    ),
)
def execute_query(snowflake: Snowflake, request: Request) -> Response:
    from nxd.drivers.rpc import Response
    import logging
    import requests as req

    log = logging.getLogger(__name__)
    if not log.handlers:
        log.addHandler(logging.StreamHandler())
    log.setLevel(logging.INFO)

    # -- Input validation -------------------------------------------------------
    sql = request.get("sql", "").strip()

    if not sql:
        return Response({"result": "No SQL provided.", "row_count": "0"})

    if not (sql.upper().lstrip().startswith("SELECT") or
            sql.upper().lstrip().startswith("WITH")):
        return Response({
            "result":    "Only SELECT or WITH queries are allowed.",
            "row_count": "0",
        })

    log.info(f"execute_query: {sql[:120]}")

    # -- Connection details -----------------------------------------------------
    account   = snowflake.account.replace("_", "-")
    user      = snowflake.user
    password  = snowflake.password
    warehouse = snowflake.warehouse
    database  = snowflake.database
    schema    = snowflake.schema
    base_url  = f"https://{account}.snowflakecomputing.com"

    mcp_url = (
        f"{base_url}/api/v2/databases/PARTNER_AZ_DB"
        f"/schemas/ACCOUNT_COVERAGE"
        f"/mcp-servers/SQL_EXEC_MCP_SRVR"
    )

    session_token = None

    try:
        # -- Login --------------------------------------------------------------
        login_resp = req.post(
            f"{base_url}/session/v1/login-request",
            params={"warehouse": warehouse, "databaseName": database, "schemaName": schema},
            json={"data": {"LOGIN_NAME": user, "PASSWORD": password}},
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=30,
        )
        login_resp.raise_for_status()
        login_data = login_resp.json()

        if not login_data.get("success"):
            msg = (login_data.get("data", {}).get("message")
                   or login_data.get("message") or "Check username and password")
            return Response({"result": f"Snowflake login failed: {msg}", "row_count": "0"})

        session_token = login_data["data"]["token"]
        log.info("Login successful")

        mcp_headers = {
            "Authorization": f'Snowflake Token="{session_token}"',
            "Content-Type":  "application/json",
            "Accept":        "application/json, text/event-stream",
        }

        # -- MCP initialize -----------------------------------------------------
        init_resp = req.post(
            mcp_url,
            json={
                "jsonrpc": "2.0", "id": "1", "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities":    {"tools": {}},
                    "clientInfo":      {"name": "account-coverage-proxy", "version": "1.0.0"},
                },
            },
            headers=dict(mcp_headers),
            timeout=30,
        )
        init_resp.raise_for_status()
        log.info("MCP initialize OK")
        log.info(f"INIT RAW RESPONSE: {init_resp.text[:500]}")
        log.info(f"INIT HEADERS: {dict(init_resp.headers)}")

        mcp_sid = init_resp.headers.get("Mcp-Session-Id", "")
        if mcp_sid:
            mcp_headers["Mcp-Session-Id"] = mcp_sid

        # -- MCP notifications/initialized --------------------------------------
        req.post(
            mcp_url,
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            headers=mcp_headers,
            timeout=10,
        )

        # -- MCP tools/call -> sql_exec_tool -------------------------------------
        call_resp = req.post(
            mcp_url,
            json={
                "jsonrpc": "2.0", "id": "2", "method": "tools/call",
                "params": {
                    "name":      "sql_exec_tool",
                    "arguments": {"sql": sql},
                },
            },
            headers=mcp_headers,
            timeout=120,
        )
        call_resp.raise_for_status()
        log.info(f"TOOL CALL STATUS: {call_resp.status_code}")
        log.info(f"TOOL CALL CONTENT-TYPE: {call_resp.headers.get('Content-Type', 'none')}")
        log.info(f"TOOL CALL RAW BODY: {call_resp.text[:1000]}")

        # -- Parse response -----------------------------------------------------
        import json as _json
        content_type = call_resp.headers.get("Content-Type", "")
        result_text  = ""

        if "text/event-stream" in content_type:
            for line in call_resp.text.splitlines():
                if not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                if not raw or raw == "[DONE]":
                    continue
                try:
                    event = _json.loads(raw)
                    if "error" in event:
                        err = event["error"]
                        return Response({"result": f"MCP error: {err.get('message', str(err))}", "row_count": "0"})
                    _res  = event.get("result", {})
                    _is_e = _res.get("isError", False)
                    for _item in _res.get("content", []):
                        if _item.get("type") == "text":
                            result_text = _item.get("text", "")
                            break
                    if _is_e:
                        return Response({"result": f"SQL error: {result_text}", "row_count": "0"})
                    if result_text:
                        break
                except Exception:
                    continue
        else:
            event = call_resp.json()
            if "error" in event:
                err = event["error"]
                return Response({"result": f"MCP error: {err.get('message', str(err))}", "row_count": "0"})
            _res  = event.get("result", {})
            _is_e = _res.get("isError", False)
            for _item in _res.get("content", []):
                if _item.get("type") == "text":
                    result_text = _item.get("text", "")
                    break
            if _is_e:
                return Response({"result": f"SQL error: {result_text}", "row_count": "0"})

        if not result_text:
            return Response({"result": "Snowflake MCP Server returned no content.", "row_count": "0"})

        _lines      = [l for l in result_text.splitlines() if l.strip()]
        _data_lines = [l for l in _lines if not all(c in "-+| " for c in l)]
        row_count   = str(max(0, len(_data_lines) - 1)) if _data_lines else "0"

        log.info(f"execute_query returned ~{row_count} rows")
        return Response({"result": result_text, "row_count": row_count})

    except req.exceptions.Timeout:
        return Response({"result": "Request timed out. Try a simpler query.", "row_count": "0"})
    except req.exceptions.HTTPError as e:
        msg = f"HTTP {e.response.status_code}: {e.response.text[:300]}"
        log.error(msg)
        return Response({"result": f"Error: {msg}", "row_count": "0"})
    except Exception as e:
        log.error(f"Unexpected error: {e}")
        return Response({"result": f"Error: {str(e)}", "row_count": "0"})
    finally:
        if session_token:
            try:
                req.delete(
                    f"{base_url}/session/logout",
                    headers={"Authorization": f'Snowflake Token="{session_token}"'},
                    timeout=10,
                )
                log.info("Session closed")
            except Exception:
                pass


# -- Tool 3: search_accounts ----------------------------------------------------
@function(name="search_accounts")
@mcp.tool(
    name="search_accounts",
    description=(
        "DEFAULT tool for any question about accounts described in plain English. "
        "Use this FIRST -- before considering execute_query. "
        "Sends the query to Snowflake MCP Server which runs Cortex Search "
        "(ACCOUNT_COVERAGE_SEARCH) for semantic similarity matching. "
        "Examples: 'find cardiology accounts with low engagement', "
        "'which high value accounts need more field visits', "
        "'oncology accounts with poor realization rates'. "
        "Do NOT use execute_query for these questions -- use this tool. "
        "No SQL needed. No schema knowledge required."
    ),
)
def search_accounts(snowflake: Snowflake, request: Request) -> Response:
    from nxd.drivers.rpc import Response
    import logging
    import requests as req

    log = logging.getLogger(__name__)
    if not log.handlers:
        log.addHandler(logging.StreamHandler())
    log.setLevel(logging.INFO)

    # -- Input validation -------------------------------------------------------
    query = request.get("query", "").strip()

    if not query:
        return Response({"result": "No search query provided.", "count": "0"})

    try:
        limit = int(request.get("limit", "10"))
        limit = max(1, min(limit, 50))
    except (ValueError, TypeError):
        limit = 10

    log.info(f"search_accounts: query='{query[:100]}', limit={limit}")

    # -- Connection details -----------------------------------------------------
    account   = snowflake.account.replace("_", "-")
    user      = snowflake.user
    password  = snowflake.password
    warehouse = snowflake.warehouse
    database  = snowflake.database
    schema    = snowflake.schema
    base_url  = f"https://{account}.snowflakecomputing.com"

    # Same Snowflake MCP Server as execute_query -- different tool called inside
    mcp_url = (
        f"{base_url}/api/v2/databases/PARTNER_AZ_DB"
        f"/schemas/ACCOUNT_COVERAGE"
        f"/mcp-servers/SQL_EXEC_MCP_SRVR"
    )

    session_token = None

    try:
        # -- Login --------------------------------------------------------------
        login_resp = req.post(
            f"{base_url}/session/v1/login-request",
            params={"warehouse": warehouse, "databaseName": database, "schemaName": schema},
            json={"data": {"LOGIN_NAME": user, "PASSWORD": password}},
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=30,
        )
        login_resp.raise_for_status()
        login_data = login_resp.json()

        if not login_data.get("success"):
            msg = (login_data.get("data", {}).get("message")
                   or login_data.get("message") or "Check username and password")
            return Response({"result": f"Snowflake login failed: {msg}", "count": "0"})

        session_token = login_data["data"]["token"]
        log.info("Login successful")

        mcp_headers = {
            "Authorization": f'Snowflake Token="{session_token}"',
            "Content-Type":  "application/json",
            "Accept":        "application/json, text/event-stream",
        }

        # -- MCP initialize -----------------------------------------------------
        init_resp = req.post(
            mcp_url,
            json={
                "jsonrpc": "2.0", "id": "1", "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities":    {"tools": {}},
                    "clientInfo":      {"name": "account-coverage-proxy", "version": "1.0.0"},
                },
            },
            headers=dict(mcp_headers),
            timeout=30,
        )
        init_resp.raise_for_status()
        log.info("MCP initialize OK")
        log.info(f"INIT RAW RESPONSE: {init_resp.text[:500]}")

        mcp_sid = init_resp.headers.get("Mcp-Session-Id", "")
        if mcp_sid:
            mcp_headers["Mcp-Session-Id"] = mcp_sid

        # -- MCP notifications/initialized --------------------------------------
        req.post(
            mcp_url,
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            headers=mcp_headers,
            timeout=10,
        )

        # -- MCP tools/call -> search_accounts_tool ------------------------------
        # search_accounts_tool is the CORTEX_SEARCH_SERVICE_QUERY tool defined
        # in CREATE MCP SERVER. The Snowflake MCP Server runs Cortex Search
        # (ACCOUNT_COVERAGE_SEARCH) internally and returns matching accounts.
        call_resp = req.post(
            mcp_url,
            json={
                "jsonrpc": "2.0", "id": "2", "method": "tools/call",
                "params": {
                    "name":      "search_accounts_tool",
                    "arguments": {
                        "query": query,
                        "limit": limit,
                    },
                },
            },
            headers=mcp_headers,
            timeout=30,
        )
        call_resp.raise_for_status()
        log.info(f"SEARCH TOOL STATUS: {call_resp.status_code}")
        log.info(f"SEARCH TOOL CONTENT-TYPE: {call_resp.headers.get('Content-Type', 'none')}")
        log.info(f"SEARCH TOOL RAW BODY: {call_resp.text[:1000]}")

        # -- Parse response -----------------------------------------------------
        import json as _json
        content_type = call_resp.headers.get("Content-Type", "")
        result_text  = ""

        if "text/event-stream" in content_type:
            for line in call_resp.text.splitlines():
                if not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                if not raw or raw == "[DONE]":
                    continue
                try:
                    event = _json.loads(raw)
                    if "error" in event:
                        err = event["error"]
                        return Response({"result": f"MCP error: {err.get('message', str(err))}", "count": "0"})
                    _res  = event.get("result", {})
                    _is_e = _res.get("isError", False)
                    for _item in _res.get("content", []):
                        if _item.get("type") == "text":
                            result_text = _item.get("text", "")
                            break
                    if _is_e:
                        return Response({"result": f"Search error: {result_text}", "count": "0"})
                    if result_text:
                        break
                except Exception:
                    continue
        else:
            event = call_resp.json()
            if "error" in event:
                err = event["error"]
                return Response({"result": f"MCP error: {err.get('message', str(err))}", "count": "0"})
            _res  = event.get("result", {})
            _is_e = _res.get("isError", False)
            for _item in _res.get("content", []):
                if _item.get("type") == "text":
                    result_text = _item.get("text", "")
                    break
            if _is_e:
                return Response({"result": f"Search error: {result_text}", "count": "0"})

        if not result_text:
            return Response({"result": "No results returned from Cortex Search.", "count": "0"})

        # Estimate count from result lines
        _lines = [l for l in result_text.splitlines() if l.strip()]
        _data  = [l for l in _lines if not all(c in "-+| " for c in l)]
        count  = str(max(0, len(_data) - 1)) if _data else "0"

        log.info(f"search_accounts returned ~{count} results")
        return Response({"result": result_text, "count": count})

    except req.exceptions.Timeout:
        return Response({"result": "Cortex Search timed out. Try again.", "count": "0"})
    except req.exceptions.HTTPError as e:
        msg = f"HTTP {e.response.status_code}: {e.response.text[:300]}"
        log.error(msg)
        return Response({"result": f"Cortex Search error: {msg}", "count": "0"})
    except Exception as e:
        log.error(f"Unexpected error: {e}")
        return Response({"result": f"Error: {str(e)}", "count": "0"})
    finally:
        if session_token:
            try:
                req.delete(
                    f"{base_url}/session/logout",
                    headers={"Authorization": f'Snowflake Token="{session_token}"'},
                    timeout=10,
                )
                log.info("Session closed")
            except Exception:
                pass
