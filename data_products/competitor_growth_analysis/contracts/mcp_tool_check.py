import json
from pathlib import Path

import requests
import yaml

QUESTION = "Do you have data about the net income growth in 2024 for competitor ANZ?"

# Configuration
DP_NAME = "competitor-growth-analysis-demo"
# TOOL_INVOKE = {"name": "get_growth", "arguments": {"symbol": "ANZ", "year": "2024"}}
TOOL_INVOKE = {"name": "get_bank_symbols", "arguments": {"year": "2024"}}

# DP_NAME = "financial-statements-demo"
# TOOL_INVOKE = {"name": "get_revenue", "arguments": {"id": "ANZ", "year": "2024"}}

# DP_NAME = "amazon-reviews-demo"
# TOOL_INVOKE = {"name": "get_average_rating_per_category", "arguments": {"category": "Headphones"}}

# Get HOST and TOKEN from ~/.nxd/config.yaml
with open(Path.home() / ".nxd" / "config.yaml") as f:
    config = yaml.safe_load(f)
    HOST = config["url"].replace("https://", "").replace("api.", "dp.")
    TOKEN = config["personal_access_token"]

PORT_NAME = "mcp-api"
ENDPOINT_PATH = "mcp"
BASE_URL = f"https://{HOST}/{DP_NAME}/rpcs/{PORT_NAME}/{ENDPOINT_PATH}/"

# BASE_URL = "https://dp.demo.trynxd.com/mcp/"


def use_mcp_tool():
    # Suppress SSL warnings for local testing
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Create session with SSL verification disabled for local testing (remove for production)
    session = requests.Session()
    session.verify = False

    # Step 1: Initialize MCP session
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "X-Nextdata-Token": TOKEN,
    }

    init_payload = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
    }

    response = session.post(BASE_URL, headers=headers, json=init_payload)
    print(f"Initialization response: {response.status_code} {response.text}")
    response.json()  # Init result (not used but confirms successful init)
    session_id = response.headers.get("Mcp-Session-Id")
    if session_id:
        headers["Mcp-Session-Id"] = session_id

    # Step 2: Send initialized notification
    initialized_payload = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    session.post(BASE_URL, headers=headers, json=initialized_payload)

    # Step 3: List available tools
    list_tools_payload = {"jsonrpc": "2.0", "id": "2", "method": "tools/list"}
    response = session.post(BASE_URL, headers=headers, json=list_tools_payload)
    tools_result = response.json()
    print(f"Available tools: {json.dumps(tools_result, indent=2)}")

    # Step 4: Call a tool
    call_tool_payload = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "tools/call",
        "params": TOOL_INVOKE,
    }
    response = session.post(BASE_URL, headers=headers, json=call_tool_payload)
    call_result = response.json()
    # print(f"Result: {json.dumps(call_result, indent=2)}")
    print(json.dumps(call_result, indent=2))

    session.close()


if __name__ == "__main__":
    use_mcp_tool()
