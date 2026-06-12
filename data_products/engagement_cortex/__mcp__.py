"""
__mcp__.py  --  engagement-cortex MCP tool.

One MCP tool, `ask`, lets an AI agent (Claude Desktop, or any MCP client)
ask natural-language questions about engagement analytics and get back the
answer along with the SQL Cortex Analyst authored to produce it. Claude
Desktop does NOT see a schema and does NOT author SQL: it forwards the
question verbatim and renders whatever this tool returns.

Architecture (the WHOLE point of this data product)
---------------------------------------------------

    Claude Desktop (natural language only)
            |
            v
    NXD MCP Proxy
            |
            v
    engagement-cortex RPC pod  (this file's `ask` tool)
            |  Snowflake REST + JSON-RPC MCP handshake
            v
    Snowflake MCP server: ENGAGEMENT_CORTEX_MCP_SRVR
            |  built-in tool: type = CORTEX_AGENT_RUN
            v
    Cortex Agent: ENGAGEMENT_ANALYST_AGENT
            |  tool: cortex_analyst_text_to_sql
            |  tool_resources.execution_environment.warehouse = ...
            v
    Cortex Analyst (text-to-SQL using engagement_analytics.yaml)
            |  generates SQL AND executes it on the configured warehouse
            v
    PARTNER_AZ_DB.ENGAGEMENT_ANALYTICS.{CHANNEL_EFFECTIVENESS, MONTHLY_TRENDS}

The Python pod here does NO SQL execution and NO text-to-SQL. It is a thin
MCP-to-MCP bridge: it logs into Snowflake with the platform-injected
credentials, runs the standard MCP handshake against the Snowflake MCP
server, calls one tool, and unwraps the response.

IMPORTANT -- why every literal is defined INSIDE a function
-----------------------------------------------------------
nxd extracts each tool function into its own generated module on the RPC pod.
It carries over module-level IMPORTS and module-level `def`/`class` statements
(so a shared helper `def` survives), but it does NOT carry over module-level
bare constant assignments (FOO = "bar"). Any such constant referenced inside
a tool becomes a NameError at runtime. Therefore:
  * Constants (MCP server name, schema, timeouts) are LOCAL to the function
    that uses them -- never module-level.
  * `Response` is re-imported inside each function body for the same reason.
  * The request/response semantic models below stay at module scope on
    purpose: they are consumed at BUILD time by nxd_spec.py, not by the
    deployed function bodies.
"""

from nxd.core.context import Snowflake
from nxd.drivers.rpc import Request
from nxd.drivers.rpc import Response
from nxd.drivers.rpc import function
from nxd.drivers.rpc import mcp
from nxd.spec import semantic_model
from nxd.spec.data_types import string


# -----------------------------------------------------------------------------
# MCP request / response models (consumed at BUILD time by nxd_spec.py).
# These module-level objects are fine where they are -- the deployed function
# bodies never reference them, so it does not matter that extraction drops
# them from the RPC pod.
# -----------------------------------------------------------------------------
ask_request = semantic_model(
    name="ask_request",
    description=(
        "A natural-language question about engagement analytics. Forward the "
        "user's question verbatim. Do NOT author SQL: Cortex Analyst will do "
        "that inside Snowflake from the semantic model. Do NOT pre-filter or "
        "rephrase columns: ask the question in plain business English."
    ),
).schema(
    {
        "question": (
            string(),
            "Plain-English question about channel effectiveness or monthly "
            "engagement trends. Examples: 'Which channel has the highest "
            "positive response rate?', 'What is the F2F to digital shift over "
            "the last 6 months?', 'Which channel is the most cost-efficient?'. "
            "Pass the user's words; the agent rephrases column-level meaning.",
        ),
    }
)

ask_response = semantic_model(
    name="ask_response",
    description=(
        "Combined answer assembled by Cortex Agent + Cortex Analyst: the "
        "business-language answer, the SQL Cortex Analyst generated, and the "
        "data the SQL returned (rendered as a tab-separated text table)."
    ),
).schema(
    {
        "answer": (
            string(),
            "Cortex Agent's natural-language answer summarising the result.",
        ),
        "sql": (
            string(),
            "The SQL Cortex Analyst authored to answer the question. Already "
            "executed against the configured warehouse; shown for transparency.",
        ),
        "data": (
            string(),
            "The executed SQL's result rendered as a tab-separated text table "
            "(header row + data rows). 'NA' when the agent did not run SQL.",
        ),
        "row_count": (
            string(),
            "Number of data rows returned, as a string ('NA' if unknown).",
        ),
    }
)


# -----------------------------------------------------------------------------
# Module-level helper. A `def` survives nxd's per-function extraction (proven
# by configure_logger in competitor_growth_analysis), so the ask tool can use
# it. Every constant it needs is LOCAL, because module-level bare constants do
# NOT survive. Raises on transport / auth failure; the caller converts that to
# a tool-friendly string.
#
# This helper does ONE thing: drive the standard Snowflake MCP JSON-RPC
# handshake against ENGAGEMENT_CORTEX_MCP_SRVR (login -> initialize ->
# notifications/initialized -> tools/call) and return the raw tools/call
# response. No SQL authoring, no SQL execution, no schema reads. Everything
# downstream of tools/call happens inside Snowflake.
# -----------------------------------------------------------------------------
def _call_cortex_mcp(snowflake, tool_name, arguments, client_name):
    import json
    import logging
    import time
    import requests as req

    # ----- LOCAL constants (module-level bare constants do NOT survive) -----
    # The Snowflake MCP server we created in deployment/04_create_mcp_server.sql.
    # It exposes ONE tool of type CORTEX_AGENT_RUN pointing at
    # ENGAGEMENT_ANALYST_AGENT.
    MCP_DATABASE = "PARTNER_AZ_DB"
    MCP_SCHEMA   = "ENGAGEMENT_CORTEX"
    MCP_SERVER   = "ENGAGEMENT_CORTEX_MCP_SRVR"

    # (connect, read) timeouts -- tuples everywhere, so one slow Cortex call
    # can never blow past the proxy's per-call window. Cortex Agent calls can
    # be long (orchestration + analyst + warehouse SQL), so the read timeout
    # on tools/call is generous.
    T_LOGIN  = (5, 25)
    T_INIT   = (5, 25)
    T_NOTIFY = (5, 10)
    T_CALL   = (5, 180)

    # Instrumented logger. The platform captures user stdout/stderr from
    # `logging` via the StreamHandler we attach. Every log line is prefixed
    # with [CX] so it can be grepped out of the framework noise in
    # proxy__getDataProductLogs.
    log = logging.getLogger("mcp.cortex")
    if not log.handlers:
        log.addHandler(logging.StreamHandler())
    log.setLevel(logging.INFO)

    def _extract_text(resp):
        """Normalise an MCP tools/call response into a string that
        _parse_agent_response can walk. For success responses we hand the
        full result envelope back as JSON text -- the parser already knows
        how to walk content[].tool_results[].content[].json{sql, result_set},
        text blocks, table blocks etc. Stripping at this layer LOSES the
        structured content (SQL and rows live inside tool_results); we used
        to do that, which is why the agent's narrative came through but
        sql/data/row_count came back empty. For errors we return a readable
        message instead.
        Handles JSON-RPC bodies and text/event-stream (SSE) bodies."""
        def _from_obj(obj):
            if isinstance(obj, dict) and obj.get("error"):
                err = obj["error"]
                msg = err.get("message", err) if isinstance(err, dict) else err
                return f"Snowflake MCP error: {msg}"
            # Success path: return the full result envelope. The parser walks
            # nested tool_results, json, text, table, etc on its own.
            result = obj.get("result", obj) if isinstance(obj, dict) else obj
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

    # --- everything below is DERIVED from the platform-injected context -----
    account   = str(snowflake.account).replace("_", "-").lower()
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

    log.info(
        "[CX] context account=%s user=%s db=%s schema=%s wh=%s tool=%s client=%s",
        account, user, database, schema, warehouse, tool_name, client_name,
    )
    log.info("[CX] target mcp_url=%s", mcp_url)
    log.info("[CX] password_present=%s", bool(password))

    # -- 1. Login -> session token -------------------------------------------
    log.info("[CX] login POST %s/session/v1/login-request", base_url)
    t0 = time.monotonic()
    try:
        login_resp = req.post(
            f"{base_url}/session/v1/login-request",
            params={"warehouse": warehouse, "databaseName": database, "schemaName": schema},
            json={"data": {"LOGIN_NAME": user, "PASSWORD": password}},
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=T_LOGIN,
        )
    except Exception as e:
        log.error("[CX] login transport error: %s: %s", type(e).__name__, e)
        raise
    login_ms = int((time.monotonic() - t0) * 1000)
    log.info("[CX] login status=%s latency_ms=%d", login_resp.status_code, login_ms)
    if login_resp.status_code >= 400:
        body_head = login_resp.text[:500]
        log.error("[CX] login HTTP error: %s body_head=%r", login_resp.status_code, body_head)
    login_resp.raise_for_status()
    login_data = login_resp.json()
    if not login_data.get("success"):
        msg = (login_data.get("data", {}) or {}).get("message") or "login rejected"
        log.error("[CX] login rejected by Snowflake: %s", msg)
        raise RuntimeError(f"Snowflake login failed: {msg}")
    session_token = login_data["data"]["token"]
    log.info("[CX] login OK token_len=%d", len(session_token) if session_token else 0)

    mcp_headers = {
        "Authorization": f'Snowflake Token="{session_token}"',
        "Content-Type":  "application/json",
        "Accept":        "application/json, text/event-stream",
    }

    # -- 2. initialize (capture session id) ----------------------------------
    log.info("[CX] init POST %s method=initialize", mcp_url)
    t0 = time.monotonic()
    try:
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
    except Exception as e:
        log.error("[CX] init transport error: %s: %s", type(e).__name__, e)
        raise
    init_ms = int((time.monotonic() - t0) * 1000)
    log.info(
        "[CX] init status=%s latency_ms=%d content_type=%r",
        init_resp.status_code, init_ms,
        init_resp.headers.get("Content-Type", ""),
    )
    if init_resp.status_code >= 400:
        body_head = init_resp.text[:500]
        log.error("[CX] init HTTP error: %s body_head=%r", init_resp.status_code, body_head)
    init_resp.raise_for_status()
    mcp_sid = init_resp.headers.get("Mcp-Session-Id", "")
    log.info("[CX] init OK session_id_present=%s session_id_len=%d", bool(mcp_sid), len(mcp_sid))
    if mcp_sid:
        mcp_headers["Mcp-Session-Id"] = mcp_sid

    # -- 2b. tools/list (discovery) -- non-fatal --------------------------
    # We call this every run so the actual input schema the server
    # advertises for our tool ends up in the logs. That schema is the
    # ground truth for what `arguments` shape tools/call expects -- if a
    # future deploy changes the schema (e.g. someone CREATE OR REPLACEs
    # the MCP server with a different tool definition) the [CX] tool
    # schema= log line will tell us immediately, instead of us having
    # to guess from a "X parameter is required" error.
    log.info("[CX] list_tools POST method=tools/list")
    t0 = time.monotonic()
    try:
        list_resp = req.post(
            mcp_url,
            json={"jsonrpc": "2.0", "id": "list", "method": "tools/list"},
            headers=mcp_headers,
            timeout=T_INIT,
        )
        list_ms = int((time.monotonic() - t0) * 1000)
        log.info(
            "[CX] list_tools status=%s latency_ms=%d",
            list_resp.status_code, list_ms,
        )
        if list_resp.status_code < 400:
            try:
                ldata = list_resp.json()
                tools = (ldata.get("result") or {}).get("tools") or []
                log.info("[CX] list_tools tool_count=%d", len(tools))
                for t in tools:
                    schema_str = json.dumps(t.get("inputSchema") or {})[:800]
                    log.info(
                        "[CX] tool name=%r description_head=%r schema=%s",
                        t.get("name"),
                        (t.get("description") or "")[:120],
                        schema_str,
                    )
            except Exception as e:
                log.warning("[CX] list_tools parse failed (non-fatal): %s: %s",
                            type(e).__name__, e)
        else:
            body_head = list_resp.text[:500]
            log.warning(
                "[CX] list_tools HTTP error (non-fatal): %s body_head=%r",
                list_resp.status_code, body_head,
            )
    except Exception as e:
        log.warning(
            "[CX] list_tools transport error (non-fatal): %s: %s",
            type(e).__name__, e,
        )

    # -- 3. notifications/initialized ----------------------------------------
    log.info("[CX] notify POST method=notifications/initialized")
    t0 = time.monotonic()
    try:
        notify_resp = req.post(
            mcp_url,
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            headers=mcp_headers,
            timeout=T_NOTIFY,
        )
        notify_ms = int((time.monotonic() - t0) * 1000)
        log.info("[CX] notify status=%s latency_ms=%d", notify_resp.status_code, notify_ms)
    except Exception as e:
        # notifications/initialized is a fire-and-forget MCP step. If the
        # server didn't accept it we'll still try tools/call -- it might work.
        log.warning("[CX] notify error (non-fatal): %s: %s", type(e).__name__, e)

    # -- 4. tools/call -> the CORTEX_AGENT_RUN tool on the MCP server --------
    # The tool arguments mirror the Cortex Agents Run REST API body: a
    # `messages` array where each message is a role + content list. The MCP
    # server forwards the call to the wrapped Cortex Agent, which orchestrates
    # the Cortex Analyst tool (which generates AND executes SQL via the
    # execution_environment configured on the agent).
    log.info("[CX] call POST tool=%s timeout_read=%ds", tool_name, T_CALL[1])
    t0 = time.monotonic()
    try:
        call_resp = req.post(
            mcp_url,
            json={
                "jsonrpc": "2.0", "id": "2", "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            },
            headers=mcp_headers,
            timeout=T_CALL,
        )
    except Exception as e:
        call_ms = int((time.monotonic() - t0) * 1000)
        log.error("[CX] call transport error after %dms: %s: %s",
                  call_ms, type(e).__name__, e)
        raise
    call_ms = int((time.monotonic() - t0) * 1000)
    ctype = call_resp.headers.get("Content-Type", "")
    body_len = len(call_resp.text) if call_resp.text is not None else 0
    log.info(
        "[CX] call status=%s latency_ms=%d content_type=%r body_len=%d",
        call_resp.status_code, call_ms, ctype, body_len,
    )
    if call_resp.status_code >= 400:
        body_head = call_resp.text[:1000]
        log.error("[CX] call HTTP error: %s body_head=%r", call_resp.status_code, body_head)
    call_resp.raise_for_status()

    # Log a head of the raw body so we can see the response shape in logs
    # (Cortex Agent responses can be 50KB+ -- only the head is useful here).
    body_head = call_resp.text[:1000]
    log.info("[CX] call body_head=%r", body_head)

    # -- 5. parse (json OR text/event-stream), then return text payload ------
    extracted = _extract_text(call_resp)
    extracted_len = len(extracted) if isinstance(extracted, str) else -1
    extracted_head = (extracted[:500] if isinstance(extracted, str) else str(extracted)[:500])
    log.info("[CX] extracted_len=%d extracted_head=%r", extracted_len, extracted_head)
    return extracted


# -----------------------------------------------------------------------------
# Module-level helper: parse a Cortex Agent response payload (which may be an
# SSE-collapsed multi-event text, a single JSON document, or an MCP-wrapped
# tools/call result) and extract the three interesting pieces:
#
#   * answer  -- the agent's final natural-language text content
#   * sql     -- the SQL Cortex Analyst authored
#   * data    -- the executed result, rendered as a tab-separated text table
#
# The Cortex Agent response shape is well-documented:
#   delta.content[*].type in {"text", "tool_use", "tool_results"}
# tool_results from cortex_analyst_text_to_sql carries:
#   tool_results.content[*].type in {"json", "text"}
#   json: {"sql": "...", "text": "...", "verified_query_used": ...}
#   plus the executed result_set (when execution_environment is configured)
# We scan for these structures across whatever envelope they arrive in.
# -----------------------------------------------------------------------------
def _parse_agent_response(raw_text):
    import json

    if not isinstance(raw_text, str) or not raw_text.strip():
        return {"answer": "", "sql": "", "data": "NA", "row_count": "NA"}

    # Accumulators -- the agent may emit incremental deltas, so we collect.
    final_text_parts = []
    sql_value = ""
    result_set = None  # dict like {"resultSetMetaData": {...}, "data": [...]}
    analyst_text = ""

    def _walk(node):
        """Recursively walk any JSON-ish structure and pluck the fields we
        care about. Robust to whether the agent response is wrapped in
        delta/content envelopes, MCP tools/call result.content envelopes, or
        a flat structure."""
        nonlocal sql_value, result_set, analyst_text
        if isinstance(node, dict):
            ntype = node.get("type")
            # tool_use blocks describe the call the agent decided to make.
            # Their `input` carries the ORIGINAL question that was forwarded
            # to the tool -- if we recurse into it we will pick up that text
            # as if it were the agent's narrative answer. Explicitly skip.
            if ntype == "tool_use":
                return
            # Cortex Analyst tool_results body
            if ntype == "tool_results":
                tr = node.get("tool_results") or {}
                for sub in tr.get("content", []) or []:
                    _walk(sub)
                return
            # json content (the analyst's structured output)
            if ntype == "json":
                j = node.get("json")
                if isinstance(j, dict):
                    if isinstance(j.get("sql"), str) and j["sql"].strip():
                        sql_value = j["sql"]
                    if isinstance(j.get("text"), str) and j["text"].strip():
                        analyst_text = j["text"]
                    # The executed result, when execution_environment is set,
                    # arrives under one of these keys depending on agent version.
                    for k in ("result_set", "resultSet", "data_result", "rows"):
                        v = j.get(k)
                        if isinstance(v, dict) and (v.get("data") is not None
                                                    or v.get("resultSetMetaData")):
                            result_set = v
                            break
                    # Some versions put rows directly under the json node.
                    if result_set is None and isinstance(j.get("data"), list):
                        meta = j.get("resultSetMetaData") or j.get("metadata")
                        if meta is not None:
                            result_set = {"resultSetMetaData": meta, "data": j["data"]}
                return
            # plain text content -- the agent's narrative answer
            if ntype == "text":
                t = node.get("text")
                if isinstance(t, str) and t.strip():
                    final_text_parts.append(t)
                return
            # walk every value
            for v in node.values():
                _walk(v)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    # The raw_text may be a single JSON object, or a stream of JSON objects
    # one per line (SSE-collapsed). Try whole, then per-line.
    parsed_any = False
    try:
        obj = json.loads(raw_text)
        _walk(obj)
        parsed_any = True
    except Exception:
        pass
    if not parsed_any:
        for line in raw_text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                _walk(json.loads(line))
                parsed_any = True
            except Exception:
                continue

    # If we never parsed anything structured, return the raw text as the answer.
    if not parsed_any:
        return {"answer": raw_text, "sql": "", "data": "NA", "row_count": "NA"}

    # Render the result_set (if any) as a tab-separated table.
    data_text = "NA"
    row_count = "NA"
    if isinstance(result_set, dict):
        meta = result_set.get("resultSetMetaData") or {}
        rowtype = meta.get("rowType") or []
        cols = [c.get("name", f"col{i}") for i, c in enumerate(rowtype)]
        rows = result_set.get("data") or []
        lines = []
        if cols:
            lines.append("\t".join(cols))
        for r in rows:
            if isinstance(r, list):
                lines.append("\t".join("" if v is None else str(v) for v in r))
            elif isinstance(r, dict):
                lines.append("\t".join("" if r.get(c) is None else str(r.get(c)) for c in cols))
            else:
                lines.append(str(r))
        rendered = "\n".join(lines).strip()
        if rendered:
            data_text = rendered
            row_count = str(len(rows))

    # Prefer the agent's narrative answer; fall back to the analyst's text.
    answer = "\n".join(p for p in final_text_parts if p).strip()
    if not answer and analyst_text:
        answer = analyst_text

    return {
        "answer":    answer or "(agent returned no narrative text)",
        "sql":       sql_value,
        "data":      data_text,
        "row_count": row_count,
    }


# -----------------------------------------------------------------------------
# Tool 1 (and only) -- ask
# -----------------------------------------------------------------------------
@function(name="ask")
@mcp.tool(
    name="ask",
    description=(
        "Ask a natural-language question about engagement analytics. "
        "Coverage: per-channel effectiveness (engagement quality, positive-"
        "response rate, on-preferred-channel rate, cost per positive response) "
        "from CHANNEL_EFFECTIVENESS, and monthly engagement trends including "
        "the F2F-to-digital channel shift from MONTHLY_TRENDS. "
        ""
        "How to call this tool: forward the user's question VERBATIM in the "
        "'question' argument. Do NOT author SQL. Do NOT fetch any schema "
        "first -- there is no get_schema tool here on purpose. Cortex Analyst "
        "inside Snowflake authors AND executes the SQL using a semantic model "
        "that knows the columns, synonyms, and verified-query patterns. "
        ""
        "Returns: 'answer' (business-language summary), 'sql' (the SQL Cortex "
        "Analyst authored; already executed), 'data' (the executed result as "
        "a tab-separated text table), 'row_count' (count of result rows). "
        ""
        "This is the ONLY tool. Answer every engagement-analytics question by "
        "calling ask exactly once with the user's words."
    ),
)
def ask(snowflake: Snowflake, request: Request) -> Response:
    import logging
    import traceback
    from nxd.drivers.rpc import Response

    # The MCP tool name on the Snowflake MCP server. This is the `name` field
    # we used in the CREATE MCP SERVER spec (see deployment/04_create_mcp_server.sql).
    # LOCAL because module-level constants do not survive extraction.
    AGENT_TOOL_NAME = "ask_engagement"

    log = logging.getLogger("mcp.ask")
    if not log.handlers:
        log.addHandler(logging.StreamHandler())
    log.setLevel(logging.INFO)
    log.info("[ASK] === ENTERED ask ===")

    question = request.get("question") or ""
    question = question.strip() if isinstance(question, str) else ""
    if not question:
        log.warning("[ASK] no question provided")
        return Response({
            "answer":    "ERROR: no question provided (expected a 'question' argument).",
            "sql":       "",
            "data":      "NA",
            "row_count": "0",
        })

    log.info("[ASK] question_len=%d preview=%r", len(question), question[:160])

    # The MCP tool's input schema (advertised via tools/list -- see the
    # [CX] tool schema log lines in _call_cortex_mcp) takes a top-level
    # `text` parameter. The server wraps it into the Cortex Agents API
    # `messages` envelope internally before forwarding to the agent.
    # We previously sent the wrapped form and got
    #   "Text parameter is required and cannot be empty"
    # back from the server because no top-level `text` was present.
    arguments = {"text": question}

    # ---- Step 1: drive the Snowflake MCP server end -----------------------
    raw = ""
    try:
        raw = _call_cortex_mcp(
            snowflake,
            tool_name=AGENT_TOOL_NAME,
            arguments=arguments,
            client_name="engagement-cortex-ask",
        )
    except Exception as e:
        # Capture the full chain so it ends up both in pod logs AND in the
        # Response the caller sees. Without the traceback we'd be flying blind.
        tb = traceback.format_exc()
        log.error("[ASK] _call_cortex_mcp raised: %s: %s\n%s", type(e).__name__, e, tb)
        return Response({
            "answer": (
                "ERROR calling Snowflake MCP server / Cortex Agent: "
                f"{type(e).__name__}: {e}\n\nTraceback:\n{tb}"
            ),
            "sql":       "",
            "data":      "NA",
            "row_count": "0",
        })

    raw_len = len(raw) if isinstance(raw, str) else -1
    log.info("[ASK] _call_cortex_mcp returned raw_len=%d", raw_len)

    # ---- Step 2: parse the agent response (CRITICAL: must not raise) ------
    # _parse_agent_response handles many response shapes but the Cortex Agent
    # output is rich and may contain unfamiliar variants. Wrap defensively so
    # a parser bug returns a real error string instead of bubbling up as an
    # opaque "Tool execution failed".
    try:
        parsed = _parse_agent_response(raw)
    except Exception as e:
        tb = traceback.format_exc()
        raw_head = (raw[:1000] if isinstance(raw, str) else str(raw)[:1000])
        log.error(
            "[ASK] _parse_agent_response raised: %s: %s\n%s",
            type(e).__name__, e, tb,
        )
        log.error("[ASK] raw_head=%r", raw_head)
        return Response({
            "answer": (
                "ERROR parsing Cortex Agent response: "
                f"{type(e).__name__}: {e}\n\n"
                f"Traceback:\n{tb}\n\n"
                f"Raw response head (first 1000 chars):\n{raw_head}"
            ),
            "sql":       "",
            "data":      "NA",
            "row_count": "0",
        })

    log.info(
        "[ASK] parsed sql_present=%s rows=%s answer_len=%d",
        "yes" if parsed.get("sql") else "no",
        parsed.get("row_count"),
        len(parsed.get("answer", "")),
    )
    log.info("[ASK] === ask RETURNING OK ===")
    return Response(parsed)