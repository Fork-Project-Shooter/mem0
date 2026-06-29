import json
import os
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from mem0_adapter import DEFAULT_USER_ID, LocalMem0Adapter


adapter = LocalMem0Adapter()
MCP_HOST = os.getenv("MEM0_LOCAL_MCP_HOST", "127.0.0.1")
MCP_PORT = int(os.getenv("MEM0_LOCAL_MCP_PORT", "8000"))
MCP_PATH = os.getenv("MEM0_LOCAL_MCP_PATH", "/mcp")
MCP_TRANSPORT = os.getenv("MEM0_LOCAL_MCP_TRANSPORT", "stdio")
MCP_PUBLIC = os.getenv("MEM0_LOCAL_MCP_PUBLIC", "false").lower() in {"1", "true", "yes"}

mcp = FastMCP(
    "mem0-local",
    host=MCP_HOST,
    port=MCP_PORT,
    streamable_http_path=MCP_PATH,
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=not MCP_PUBLIC),
)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


@mcp.tool(description="Search local personal memories relevant to a query.")
def memory_search(query: str, user_id: str = DEFAULT_USER_ID, scope: Optional[str] = None, limit: int = 5) -> str:
    return _json(adapter.search(query=query, user_id=user_id, scope=scope, limit=limit))


@mcp.tool(description="Add a durable local personal memory. Use infer=False to store content verbatim.")
def memory_add(
    content: str,
    user_id: str = DEFAULT_USER_ID,
    type: str = "preference",
    scope: str = "general",
    confidence: str = "medium",
    stability: str = "stable",
    metadata: Optional[Dict[str, Any]] = None,
    infer: bool = True,
) -> str:
    return _json(
        adapter.add(
            content=content,
            user_id=user_id,
            memory_type=type,
            scope=scope,
            confidence=confidence,
            stability=stability,
            metadata=metadata,
            infer=infer,
        )
    )


@mcp.tool(description="List local personal memories for a user and optional scope.")
def memory_list(user_id: str = DEFAULT_USER_ID, scope: Optional[str] = None, limit: int = 50) -> str:
    return _json(adapter.list(user_id=user_id, scope=scope, limit=limit))


@mcp.tool(description="Get one local personal memory by id.")
def memory_get(memory_id: str) -> str:
    return _json(adapter.get(memory_id))


@mcp.tool(description="Update a local personal memory by id.")
def memory_update(memory_id: str, content: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
    return _json(adapter.update(memory_id=memory_id, content=content, metadata=metadata))


@mcp.tool(description="Delete one local personal memory by id.")
def memory_delete(memory_id: str) -> str:
    return _json(adapter.delete(memory_id))


@mcp.tool(description="Delete all local personal memories for a user.")
def memory_delete_all(user_id: str = DEFAULT_USER_ID) -> str:
    return _json(adapter.delete_all(user_id=user_id))


@mcp.tool(description="Return local personal memory MCP status.")
def memory_health() -> str:
    return _json(adapter.health())


if __name__ == "__main__":
    mcp.run(transport=MCP_TRANSPORT)
