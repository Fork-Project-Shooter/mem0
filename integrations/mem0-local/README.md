# Mem0 Local Codex Plugin

This plugin exposes local Mem0 memory to Codex through a stdio MCP server.

Architecture:

```text
Codex -> personal-memory skill -> local MCP tools -> Mem0 adapter -> Mem0 Python SDK -> local Qdrant/SQLite storage
```

No OpenMemory dashboard or HTTP server is required.

## Configure

Edit `mcp-server/mem0_adapter.py`:

```python
DEEPSEEK_API_KEY = "your-deepseek-api-key"
EMBEDDER = "hash"       # bootstrap mode, no model download
# EMBEDDER = "fastembed"  # real local embeddings, first run downloads model
```

`hash` mode is useful when FastEmbed cannot download its model. It is enough to verify the local MCP flow, but real semantic retrieval should use FastEmbed or another proper embedder.

## Install Dependencies

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[extras]"
.\.venv\Scripts\python.exe -m pip install "mcp[cli]>=1.25.4"
```

## Codex MCP

The plugin MCP config is:

```json
{
  "mcpServers": {
    "mem0-local": {
      "command": "D:\\Projects\\mem0\\.venv\\Scripts\\python.exe",
      "args": ["D:\\Projects\\mem0\\integrations\\mem0-local\\mcp-server\\server.py"]
    }
  }
}
```

If the repository path changes, update `integrations/mem0-local/.mcp.json`.

## Tools

- `memory_search(query, user_id="me", scope=None, limit=5)`
- `memory_add(content, user_id="me", type="preference", scope="general", confidence="medium", stability="stable", metadata=None, infer=True)`
- `memory_list(user_id="me", scope=None, limit=50)`
- `memory_get(memory_id)`
- `memory_update(memory_id, content=None, metadata=None)`
- `memory_delete(memory_id)`
- `memory_delete_all(user_id="me")`
- `memory_health()`

## Local Data

Data is stored under:

```text
~/.mem0-local/
```
