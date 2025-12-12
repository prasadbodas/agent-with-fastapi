from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import sqlite3
import os
import json
import logging
from typing import Optional
from datetime import datetime
from langchain_mcp_adapters.client import MultiServerMCPClient

router = APIRouter()


DB_PATH = os.getenv("DB_PATH", "odoo_agent.db")

# Module-level MCP client
mcp_client: Optional[MultiServerMCPClient] = None

logger = logging.getLogger(__name__)


def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def ensure_mcps_table():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS mcps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        transport TEXT NOT NULL,
        url TEXT,
        command TEXT,
        args TEXT,
        metadata TEXT DEFAULT '{}',
        active INTEGER DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME
    )
    """)
    conn.commit()
    cur.close()
    conn.close()


def list_mcps():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name, transport, url, command, args, metadata, active, created_at, updated_at FROM mcps ORDER BY id ASC")
    rows = cur.fetchall()
    cols = ["id", "name", "transport", "url", "command", "args", "metadata", "active", "created_at", "updated_at"]
    result = [dict(zip(cols, r)) for r in rows]
    cur.close()
    conn.close()
    return result


def get_mcp(mcp_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name, transport, url, command, args, metadata, active, created_at, updated_at FROM mcps WHERE id = ?", (mcp_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    cols = ["id", "name", "transport", "url", "command", "args", "metadata", "active", "created_at", "updated_at"]
    return dict(zip(cols, row))


def save_mcp(data: dict):
    conn = get_conn()
    cur = conn.cursor()
    args_json = json.dumps(data.get("args")) if data.get("args") is not None else None
    metadata = json.dumps(data.get("metadata")) if data.get("metadata") is not None else "{}"
    cur.execute(
        "INSERT INTO mcps (name, transport, url, command, args, metadata, active) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (data.get("name"), data.get("transport"), data.get("url"), data.get("command"), args_json, metadata, 1 if data.get("active", True) else 0)
    )
    conn.commit()
    last_id = cur.lastrowid
    cur.close()
    conn.close()
    return last_id


def update_mcp(mcp_id: int, data: dict):
    conn = get_conn()
    cur = conn.cursor()
    existing = get_mcp(mcp_id)
    if not existing:
        cur.close()
        conn.close()
        return None
    args_json = json.dumps(data.get("args")) if data.get("args") is not None else existing["args"]
    metadata = json.dumps(data.get("metadata")) if data.get("metadata") is not None else existing["metadata"]
    cur.execute(
        "UPDATE mcps SET name = ?, transport = ?, url = ?, command = ?, args = ?, metadata = ?, active = ?, updated_at = ? WHERE id = ?",
        (
            data.get("name", existing["name"]),
            data.get("transport", existing["transport"]),
            data.get("url", existing["url"]),
            data.get("command", existing["command"]),
            args_json,
            metadata,
            1 if data.get("active", existing["active"]) else 0,
            datetime.utcnow(),
            mcp_id,
        )
    )
    conn.commit()
    cur.close()
    conn.close()
    return get_mcp(mcp_id)


def delete_mcp(mcp_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM mcps WHERE id = ?", (mcp_id,))
    conn.commit()
    deleted = cur.rowcount
    cur.close()
    conn.close()
    return deleted


def build_servers_map(rows):
    servers = {}
    for r in rows:
        if not r.get("active"):
            continue
        name = r.get("name")
        transport = r.get("transport")
        if transport == "http":
            servers[name] = {"url": r.get("url"), "transport": "streamable_http"}
        elif transport == "stdio":
            args = []
            try:
                args = json.loads(r.get("args") or "[]")
            except Exception:
                args = []
            servers[name] = {"command": r.get("command"), "args": args, "transport": "stdio"}

        else:
            # Fallback: store as url
            servers[name] = {"url": r.get("url"), "transport": "streamable_http"}
    return servers


async def reload_mcp_client():
    global mcp_client
    ensure_mcps_table()
    rows = list_mcps()
    servers = build_servers_map(rows)
    if not servers:
        mcp_client = None
        return {"success": True, "message": "No MCPs configured"}
    mcp_client = MultiServerMCPClient(servers)
    # try to warm up tools
    try:
        tools = await mcp_client.get_tools()
    except Exception as e:
        logger.exception("Failed to get tools from MCPs: %s", e)
        return {"success": False, "error": str(e)}
    # Prepare simple tool summary (safe id fallback to name)
    tools_summary = [{"name": getattr(t, "name", None), "id": getattr(t, "id", getattr(t, "name", None))} for t in tools] if tools else []
    return {"success": True, "tools": tools_summary}


def get_mcp_client():
    global mcp_client
    return mcp_client


@router.get("/chat-mcp")
async def get_mcp_ui():
    return FileResponse("frontend/index-mcp.html")


@router.get("/mcp/list")
async def api_list_mcps():
    ensure_mcps_table()
    rows = list_mcps()
    # Make sure args & metadata are parsed into JSON
    for r in rows:
        try:
            r["args"] = json.loads(r["args"]) if r.get("args") else []
        except Exception:
            r["args"] = []
        try:
            r["metadata"] = json.loads(r["metadata"]) if r.get("metadata") else {}
        except Exception:
            r["metadata"] = {}
    return JSONResponse({"mcps": rows})


@router.post("/mcp")
async def api_add_mcp(request: Request):
    body = await request.json()
    if not body.get("name") or not body.get("transport"):
        raise HTTPException(status_code=400, detail="Missing required fields: 'name' and 'transport'")
    if body["transport"] == "http" and not body.get("url"):
        raise HTTPException(status_code=400, detail="HTTP transport requires 'url'")
    if body["transport"] == "stdio" and not body.get("command"):
        raise HTTPException(status_code=400, detail="STDIO transport requires 'command'")
    mc_id = save_mcp(body)
    return JSONResponse({"success": True, "id": mc_id})


@router.put("/mcp/{mcp_id}")
async def api_update_mcp(mcp_id: int, request: Request):
    body = await request.json()
    updated = update_mcp(mcp_id, body)
    if not updated:
        raise HTTPException(status_code=404, detail="MCP not found")
    return JSONResponse({"success": True, "mcp": updated})


@router.delete("/mcp/{mcp_id}")
async def api_delete_mcp(mcp_id: int):
    deleted = delete_mcp(mcp_id)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="MCP not found")
    return JSONResponse({"success": True, "deleted": deleted})


@router.post("/mcp/reload")
async def api_reload_mcp():
    res = await reload_mcp_client()
    if not res.get("success"):
        raise HTTPException(status_code=500, detail=res.get("error"))
    return JSONResponse(res)


@router.get("/mcp/tools")
async def api_get_mcp_tools():
    client = get_mcp_client()
    if not client:
        return JSONResponse({"tools": []})
    tools = await client.get_tools()
    tools_summary = [{"name": getattr(t, "name", None), "id": getattr(t, "id", getattr(t, "name", None))} for t in tools] if tools else []
    return JSONResponse({"tools": tools_summary})


@router.post("/mcp/test")
async def api_test_mcp(request: Request):
    body = await request.json()
    servers = {}
    name = body.get("name", "test")
    transport = body.get("transport")
    if transport == "http":
        servers[name] = {"url": body.get("url"), "transport": "streamable_http"}
    elif transport == "stdio":
        servers[name] = {"command": body.get("command"), "args": body.get("args", []), "transport": "stdio"}
    else:
        raise HTTPException(status_code=400, detail="Unknown transport")
    try:
        client = MultiServerMCPClient(servers)
        tools = await client.get_tools()
        tools_summary = [{"name": getattr(t, "name", None), "id": getattr(t, "id", getattr(t, "name", None))} for t in tools] if tools else []
        return JSONResponse({"success": True, "tools": tools_summary})
    except Exception as e:
        logger.exception("Failed to test MCP: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
