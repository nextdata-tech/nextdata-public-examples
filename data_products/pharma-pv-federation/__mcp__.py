"""
__mcp__.py — pharma-pv-federation MCP tools

get_metadata
    Returns live INFORMATION_SCHEMA metadata for the two federated
    pharmacovigilance tables, their join keys, and the key metric formula.
    Call first so the SQL you write uses correct column names.

execute_federated_query
    Runs a SELECT / WITH statement in Snowflake via the Snowflake MCP Server
    (SQL_EXEC_MCP_SRVR in the ACCOUNT_COVERAGE schema — same object used by
    the account-coverage data product; this product runs as the same
    PARTNER_AZ_ROLE so it already has access).

All imports are inside function bodies (nxd restricted scope).
"""

from nxd.core.context import Snowflake
from nxd.drivers.rpc import Request
from nxd.drivers.rpc import Response
from nxd.drivers.rpc import function
from nxd.drivers.rpc import mcp


@function(name="get_metadata")
@mcp.tool(
    name="get_metadata",
    description=(
        "Live schema metadata for the two federated pharmacovigilance tables: "
        "adverse_event_summary (Drug Safety domain — adverse-event counts, the numerator) "
        "and prescription_volume (Commercial domain — prescription volume, the denominator). "
        "Returns real column names and types from INFORMATION_SCHEMA, the join keys "
        "(product_id, region, report_period), and the key federated metric formula "
        "(adverse-event reporting rate per 1,000 prescriptions). "
        "Call this FIRST before execute_federated_query."
    ),
)
def get_metadata(snowflake: Snowflake, request: Request) -> Response:
    import json as _json
    import logging
    import re as _re
    import requests as req
    from nxd.drivers.rpc import Response

    log = logging.getLogger("mcp.get_metadata")
    if not log.handlers:
        log.addHandler(logging.StreamHandler())
    log.setLevel(logging.INFO)
    log.info("=== ENTERED get_metadata ===")

    # SQL_EXEC_MCP_SRVR lives in ACCOUNT_COVERAGE (created in Phase 1).
    # This product runs as PARTNER_AZ_ROLE — same role as account-coverage — so
    # it has access. We must target this schema; the orchestrator's own schema
    # (pharma_pv_federation) has no MCP Server object.
    MCP_SCHEMA      = "ACCOUNT_COVERAGE"
    SAFETY_SCHEMA   = "drug_safety_signals"
    SAFETY_TABLE    = "adverse_event_summary"
    COMM_SCHEMA     = "commercial_prescriptions"
    COMM_TABLE      = "prescription_volume"

    account  = snowflake.account.replace("_", "-")
    user     = snowflake.user
    password = snowflake.password
    wh       = snowflake.warehouse
    database = (request.get("database") or getattr(snowflake, "database", "") or "").strip()
    base_url = f"https://{account}.snowflakecomputing.com"
    mcp_url  = (
        f"{base_url}/api/v2/databases/{database}"
        f"/schemas/{MCP_SCHEMA}/mcp-servers/SQL_EXEC_MCP_SRVR"
    )

    if not database:
        return Response({"metadata": "No database resolved. Pass 'database' explicitly.", "source": "none"})
    if not _re.match(r"^[A-Za-z_][A-Za-z0-9_$]*$", database):
        return Response({"metadata": f"Invalid database identifier: '{database[:40]}'.", "source": "none"})

    info_sql = (
        "SELECT table_schema, table_name, column_name, data_type, "
        "COALESCE(comment,'') AS col_comment, ordinal_position "
        f"FROM {database}.INFORMATION_SCHEMA.COLUMNS "
        f"WHERE (LOWER(table_schema)=LOWER('{SAFETY_SCHEMA}') AND LOWER(table_name)=LOWER('{SAFETY_TABLE}')) "
        f"   OR (LOWER(table_schema)=LOWER('{COMM_SCHEMA}') AND LOWER(table_name)=LOWER('{COMM_TABLE}')) "
        "ORDER BY table_name, ordinal_position"
    )

    session_token = None
    info_text = ""
    try:
        lr = req.post(
            f"{base_url}/session/v1/login-request",
            params={"warehouse": wh, "databaseName": database, "schemaName": MCP_SCHEMA},
            json={"data": {"LOGIN_NAME": user, "PASSWORD": password}},
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=(5, 15),
        )
        lr.raise_for_status()
        ld = lr.json()
        if not ld.get("success"):
            msg = ld.get("data",{}).get("message") or ld.get("message","Check credentials")
            return Response({"metadata": f"Snowflake login failed: {msg}", "source": "none"})
        session_token = ld["data"]["token"]
        log.info("login OK")

        h = {
            "Authorization": f'Snowflake Token="{session_token}"',
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        ir = req.post(
            mcp_url,
            json={"jsonrpc":"2.0","id":"1","method":"initialize",
                  "params":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"clientInfo":{"name":"pharma-pv-federation","version":"1.0"}}},
            headers=dict(h), timeout=(5, 15),
        )
        ir.raise_for_status()
        sid = ir.headers.get("Mcp-Session-Id","")
        if sid:
            h["Mcp-Session-Id"] = sid
        req.post(mcp_url, json={"jsonrpc":"2.0","method":"notifications/initialized"}, headers=h, timeout=10)

        cr = req.post(
            mcp_url,
            json={"jsonrpc":"2.0","id":"2","method":"tools/call",
                  "params":{"name":"sql_exec_tool","arguments":{"sql":info_sql}}},
            headers=h, timeout=(5, 30),
        )
        cr.raise_for_status()
        log.info(f"info_schema call status={cr.status_code}")

        ct = cr.headers.get("Content-Type","")
        if "text/event-stream" in ct:
            for line in cr.text.splitlines():
                if not line.startswith("data:"): continue
                raw = line[5:].strip()
                if not raw or raw == "[DONE]": continue
                try:
                    ev = _json.loads(raw)
                    if "error" in ev:
                        info_text = f"__ERR__:{ev['error'].get('message',str(ev['error']))}"; break
                    _r = ev.get("result",{})
                    for _c in _r.get("content",[]):
                        if _c.get("type")=="text": info_text=_c.get("text",""); break
                    if _r.get("isError"): info_text=f"__ERR__:{info_text}"; break
                    if info_text: break
                except Exception: continue
        else:
            ev = cr.json()
            if "error" in ev:
                info_text = f"__ERR__:{ev['error'].get('message',str(ev['error']))}"
            else:
                _r = ev.get("result",{})
                for _c in _r.get("content",[]):
                    if _c.get("type")=="text": info_text=_c.get("text",""); break
                if _r.get("isError"): info_text=f"__ERR__:{info_text}"

    except req.exceptions.Timeout:
        return Response({"metadata":"Metadata query timed out.","source":"none"})
    except req.exceptions.HTTPError as e:
        return Response({"metadata":f"HTTP {e.response.status_code}: {e.response.text[:200]}","source":"none"})
    except Exception as e:
        log.error(f"error: {e}")
        return Response({"metadata":f"Error: {str(e)[:200]}","source":"none"})
    finally:
        if session_token:
            try:
                req.delete(f"{base_url}/session/logout",
                           headers={"Authorization":f'Snowflake Token="{session_token}"'}, timeout=10)
            except Exception: pass

    header = (
        f"FEDERATED PHARMACOVIGILANCE TABLES (database: {database})\n\n"
        f"TABLE A — Drug Safety domain (adverse events — the NUMERATOR):\n"
        f"  {database}.{SAFETY_SCHEMA}.{SAFETY_TABLE}\n"
        f"  Owned by Pharmacovigilance. Has AE counts but NO prescription denominator.\n\n"
        f"TABLE B — Commercial domain (prescription volume — the DENOMINATOR):\n"
        f"  {database}.{COMM_SCHEMA}.{COMM_TABLE}\n"
        f"  Owned by Commercial Analytics. Has Rx volume but NO safety data.\n\n"
        f"JOIN KEYS: product_id, region, report_period\n\n"
        f"KEY FEDERATED METRIC (neither table has it alone):\n"
        f"  reporting_rate_per_1k_rx = adverse_event_count * 1000.0 / total_prescriptions\n\n"
        f"LIVE COLUMNS (from INFORMATION_SCHEMA):\n"
    )

    if info_text.startswith("__ERR__:"):
        return Response({"metadata": header + f"Could not read columns: {info_text[8:]}", "source": "none"})

    body = info_text.strip() or "  (no columns returned — check that source DPs have deployed)"

    example = (
        f"\n\nEXAMPLE — reporting rate per 1,000 Rx by product and region (2025-Q3):\n"
        f"SELECT s.product_name, s.region,\n"
        f"       s.adverse_event_count, c.total_prescriptions,\n"
        f"       ROUND(s.adverse_event_count * 1000.0 / c.total_prescriptions, 1)\n"
        f"         AS reporting_rate_per_1k_rx,\n"
        f"       ROUND(s.serious_event_count * 1000.0 / c.total_prescriptions, 1)\n"
        f"         AS serious_rate_per_1k_rx,\n"
        f"       s.top_reaction_group\n"
        f"FROM {database}.{SAFETY_SCHEMA}.{SAFETY_TABLE} s\n"
        f"JOIN {database}.{COMM_SCHEMA}.{COMM_TABLE} c\n"
        f"  ON  s.product_id    = c.product_id\n"
        f"  AND s.region        = c.region\n"
        f"  AND s.report_period = c.report_period\n"
        f"WHERE s.report_period = '2025-Q3'\n"
        f"ORDER BY reporting_rate_per_1k_rx DESC;"
    )

    log.info("=== get_metadata RETURNING OK ===")
    return Response({"metadata": header + body + example, "source": "information_schema"})


@function(name="execute_federated_query")
@mcp.tool(
    name="execute_federated_query",
    description=(
        "Execute a SQL SELECT (cross-domain pharmacovigilance JOIN) in Snowflake. "
        "Joins adverse_event_summary (Drug Safety) with prescription_volume (Commercial) "
        "on product_id, region, report_period to compute the adverse-event reporting rate "
        "per 1,000 prescriptions. Use fully-qualified names such as "
        "PARTNER_AZ_DB.drug_safety_signals.adverse_event_summary. "
        "Call get_metadata first. Only SELECT or WITH statements are allowed."
    ),
)
def execute_federated_query(snowflake: Snowflake, request: Request) -> Response:
    import json as _json
    import logging
    import requests as req
    from nxd.drivers.rpc import Response

    log = logging.getLogger("mcp.execute_federated_query")
    if not log.handlers:
        log.addHandler(logging.StreamHandler())
    log.setLevel(logging.INFO)
    log.info("=== ENTERED execute_federated_query ===")

    MCP_SCHEMA = "ACCOUNT_COVERAGE"

    sql = request.get("sql","").strip()
    if not sql:
        return Response({"result":"No SQL provided.","row_count":"0"})
    if not (sql.upper().lstrip().startswith("SELECT") or sql.upper().lstrip().startswith("WITH")):
        return Response({"result":"Only SELECT or WITH queries are allowed.","row_count":"0"})

    _body = sql.rstrip().rstrip(";")
    if " LIMIT " not in f" {_body.upper()} ":
        sql = f"{_body} LIMIT 1000"
    else:
        sql = _body

    account  = snowflake.account.replace("_","-")
    user     = snowflake.user
    password = snowflake.password
    wh       = snowflake.warehouse
    database = (getattr(snowflake,"database","") or "").strip()
    base_url = f"https://{account}.snowflakecomputing.com"
    mcp_url  = (
        f"{base_url}/api/v2/databases/{database}"
        f"/schemas/{MCP_SCHEMA}/mcp-servers/SQL_EXEC_MCP_SRVR"
    )

    session_token = None
    try:
        lr = req.post(
            f"{base_url}/session/v1/login-request",
            params={"warehouse": wh, "databaseName": database, "schemaName": MCP_SCHEMA},
            json={"data": {"LOGIN_NAME": user, "PASSWORD": password}},
            headers={"Content-Type":"application/json","Accept":"application/json"},
            timeout=(5, 15),
        )
        lr.raise_for_status()
        ld = lr.json()
        if not ld.get("success"):
            msg = ld.get("data",{}).get("message") or ld.get("message","Check credentials")
            return Response({"result":f"Login failed: {msg}","row_count":"0"})
        session_token = ld["data"]["token"]
        log.info("login OK")

        h = {
            "Authorization": f'Snowflake Token="{session_token}"',
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        ir = req.post(
            mcp_url,
            json={"jsonrpc":"2.0","id":"1","method":"initialize",
                  "params":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"clientInfo":{"name":"pharma-pv-federation","version":"1.0"}}},
            headers=dict(h), timeout=(5, 15),
        )
        ir.raise_for_status()
        sid = ir.headers.get("Mcp-Session-Id","")
        if sid:
            h["Mcp-Session-Id"] = sid
        req.post(mcp_url, json={"jsonrpc":"2.0","method":"notifications/initialized"}, headers=h, timeout=10)

        cr = req.post(
            mcp_url,
            json={"jsonrpc":"2.0","id":"2","method":"tools/call",
                  "params":{"name":"sql_exec_tool","arguments":{"sql":sql}}},
            headers=h, timeout=(5, 40),
        )
        cr.raise_for_status()
        log.info(f"query status={cr.status_code}")

        ct = cr.headers.get("Content-Type","")
        result_text = ""
        if "text/event-stream" in ct:
            for line in cr.text.splitlines():
                if not line.startswith("data:"): continue
                raw = line[5:].strip()
                if not raw or raw=="[DONE]": continue
                try:
                    ev = _json.loads(raw)
                    if "error" in ev:
                        return Response({"result":f"MCP error: {ev['error'].get('message',str(ev['error']))}","row_count":"0"})
                    _r = ev.get("result",{})
                    for _c in _r.get("content",[]):
                        if _c.get("type")=="text": result_text=_c.get("text",""); break
                    if _r.get("isError"):
                        return Response({"result":f"SQL error: {result_text}","row_count":"0"})
                    if result_text: break
                except Exception: continue
        else:
            ev = cr.json()
            if "error" in ev:
                return Response({"result":f"MCP error: {ev['error'].get('message',str(ev['error']))}","row_count":"0"})
            _r = ev.get("result",{})
            for _c in _r.get("content",[]):
                if _c.get("type")=="text": result_text=_c.get("text",""); break
            if _r.get("isError"):
                return Response({"result":f"SQL error: {result_text}","row_count":"0"})

        if not result_text:
            return Response({"result":"Snowflake returned no content.","row_count":"0"})

        _dl = [l for l in result_text.splitlines() if l.strip() and not all(c in "-+| " for c in l)]
        log.info("=== execute_federated_query RETURNING OK ===")
        return Response({"result": result_text, "row_count": str(max(0, len(_dl)-1))})

    except req.exceptions.Timeout:
        return Response({"result":"Query timed out.","row_count":"0"})
    except req.exceptions.HTTPError as e:
        return Response({"result":f"HTTP {e.response.status_code}: {e.response.text[:200]}","row_count":"0"})
    except Exception as e:
        log.error(f"error: {e}")
        return Response({"result":f"Error: {str(e)}","row_count":"0"})
    finally:
        if session_token:
            try:
                req.delete(f"{base_url}/session/logout",
                           headers={"Authorization":f'Snowflake Token="{session_token}"'}, timeout=10)
            except Exception: pass
