#!/usr/bin/env python3
"""Minimal Infisical MCP server — wraps Infisical REST API via JSON-RPC over stdin/stdout."""

import json
import os
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

HOST = os.environ.get("INFISICAL_HOST_URL", "http://192.168.0.16:8081")
TOKEN = os.environ.get("INFISICAL_ACCESS_TOKEN", "")
UNIVERSAL_CLIENT_ID = os.environ.get("INFISICAL_UNIVERSAL_AUTH_CLIENT_ID", "")
UNIVERSAL_CLIENT_SECRET = os.environ.get("INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET", "")
DEFAULT_PROJECT = os.environ.get("INFISICAL_DEFAULT_PROJECT_ID", "")


def auth_headers():
    """Return headers for authenticated requests."""
    if TOKEN:
        return {"Authorization": f"Bearer {TOKEN}"}
    if UNIVERSAL_CLIENT_ID and UNIVERSAL_CLIENT_SECRET:
        # Universal Auth flow: exchange client credentials for access token
        url = f"{HOST}/api/v1/auth/universal-auth/login/"
        body = json.dumps({
            "clientId": UNIVERSAL_CLIENT_ID,
            "clientSecret": UNIVERSAL_CLIENT_SECRET
        }).encode()
        req = Request(url, data=body, headers={"Content-Type": "application/json"})
        resp = urlopen(req)
        data = json.loads(resp.read())
        return {"Authorization": f"Bearer {data['accessToken']}"}
    raise RuntimeError("No authentication configured (INFISICAL_ACCESS_TOKEN or INFISICAL_UNIVERSAL_AUTH_* required)")


def infisical_get(path, params=None):
    """GET request to Infisical API."""
    url = f"{HOST}/api/v1{path}"
    if params:
        from urllib.parse import urlencode
        url += "?" + urlencode(params)
    req = Request(url, headers=auth_headers())
    resp = urlopen(req)
    return json.loads(resp.read())


def infisical_post(path, body):
    """POST request to Infisical API."""
    url = f"{HOST}/api/v1{path}"
    data = json.dumps(body).encode()
    req = Request(url, data=data, headers={**auth_headers(), "Content-Type": "application/json"})
    resp = urlopen(req)
    return json.loads(resp.read())


def list_secrets(project_id=None, environment="dev"):
    """List all secrets in a project/environment."""
    pid = project_id or DEFAULT_PROJECT
    if not pid:
        raise RuntimeError("No default project configured (INFISICAL_DEFAULT_PROJECT_ID)")
    data = infisical_get(f"/projects/{pid}/secrets", {"environment": environment})
    return {
        "project_id": pid,
        "environment": environment,
        "secrets": [
            {
                "id": s.get("secretKey"),
                "key": s.get("secretKey"),
                "value": s.get("secretValue", ""),
                "version": s.get("version"),
                "type": s.get("type", "plaintext")
            }
            for s in data.get("secrets", [])
        ]
    }


def get_secret_by_path(project_id=None, path="", environment="dev"):
    """Get a secret by its full path."""
    pid = project_id or DEFAULT_PROJECT
    if not pid:
        raise RuntimeError("No default project configured")
    data = infisical_get(f"/projects/{pid}/secrets/by-path/{path}", {"environment": environment})
    return {
        "project_id": pid,
        "environment": environment,
        "secret": {
            "id": data.get("secretKey"),
            "key": data.get("secretKey"),
            "value": data.get("secretValue", ""),
            "version": data.get("version"),
            "type": data.get("type", "plaintext")
        }
    }


def get_secret_by_id(project_id=None, secret_id="", environment="dev"):
    """Get a specific secret by its ID."""
    pid = project_id or DEFAULT_PROJECT
    if not pid:
        raise RuntimeError("No default project configured")
    data = infisical_get(f"/projects/{pid}/secrets/by-id/{secret_id}", {"environment": environment})
    return {
        "project_id": pid,
        "environment": environment,
        "secret": {
            "id": data.get("secretKey"),
            "key": data.get("secretKey"),
            "value": data.get("secretValue", ""),
            "version": data.get("version"),
            "type": data.get("type", "plaintext")
        }
    }


def get_project_info(project_id=None):
    """Get project metadata."""
    pid = project_id or DEFAULT_PROJECT
    if not pid:
        raise RuntimeError("No default project configured")
    return infisical_get(f"/projects/{pid}")


# MCP tool definitions (static — published on tools/list)
TOOLS = [
    {
        "name": "infisical_list_secrets",
        "description": "List all secrets in a project and environment. Returns key-value pairs with metadata.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Project ID (defaults to INFISICAL_DEFAULT_PROJECT_ID)"},
                "environment": {"type": "string", "default": "dev", "description": "Environment name (e.g. dev, staging, prod)"}
            },
            "required": []
        }
    },
    {
        "name": "infisical_get_secret_by_path",
        "description": "Get a specific secret by its full path (e.g. /database/host). Returns the key-value pair.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "path": {"type": "string", "description": "Full secret path, e.g. /database/host"},
                "environment": {"type": "string", "default": "dev"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "infisical_get_secret_by_id",
        "description": "Get a specific secret by its unique ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "secret_id": {"type": "string", "description": "Secret UUID"},
                "environment": {"type": "string", "default": "dev"}
            },
            "required": ["secret_id"]
        }
    },
    {
        "name": "infisical_get_project_info",
        "description": "Get project metadata (name, environments, etc.).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"}
            },
            "required": []
        }
    }
]


def handle_request(req):
    """Process a single JSON-RPC request and return response dict."""
    method = req.get("method", "")
    params = req.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req["id"],
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}, "resources": {}},
                "serverInfo": {"name": "infisical-mcp-py", "version": "1.0.0"}
            }
        }

    if method == "notifications/initialized":
        return None  # no response for notifications

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req["id"],
            "result": {"tools": TOOLS}
        }

    if method.startswith("tools/call"):
        tool_name = params.get("name", "")
        args = params.get("arguments", {})

        try:
            if tool_name == "infisical_list_secrets":
                result = list_secrets(args.get("project_id"), args.get("environment", "dev"))
            elif tool_name == "infisical_get_secret_by_path":
                result = get_secret_by_path(args.get("project_id"), args["path"], args.get("environment", "dev"))
            elif tool_name == "infisical_get_secret_by_id":
                result = get_secret_by_id(args.get("project_id"), args["secret_id"], args.get("environment", "dev"))
            elif tool_name == "infisical_get_project_info":
                result = get_project_info(args.get("project_id"))
            else:
                return {"jsonrpc": "2.0", "id": req["id"], "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}}

            return {
                "jsonrpc": "2.0",
                "id": req["id"],
                "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
            }
        except HTTPError as e:
            body = e.read().decode() if e.fp else ""
            return {
                "jsonrpc": "2.0",
                "id": req["id"],
                "error": {"code": -32000, "message": f"Infisical API error ({e.code}): {body}"}
            }
        except URLError as e:
            return {
                "jsonrpc": "2.0",
                "id": req["id"],
                "error": {"code": -32000, "message": f"Connection error: {e.reason}"}
            }

    return {"jsonrpc": "2.0", "id": req.get("id"), "error": {"code": -32601, "message": f"Unknown method: {method}"}}


def main():
    print(json.dumps({"jsonrpc": "2.0", "result": None}), flush=True)  # server greeting
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            print(json.dumps({"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}}), flush=True)
            continue

        resp = handle_request(req)
        if resp is not None:
            print(json.dumps(resp), flush=True)


if __name__ == "__main__":
    main()
