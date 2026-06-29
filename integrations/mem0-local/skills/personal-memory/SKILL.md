---
name: personal-memory
description: Use when the user asks Codex to remember, retrieve, inspect, update, delete, or apply personal memories, preferences, decision rules, reasoning patterns, anti-patterns, corrections, and domain-specific judgment models through the local Mem0 MCP tools.
---

# Personal Memory

Use the local Mem0 MCP server as the external memory store. Treat memory as user preference and working context, not as a source of current external facts.

## Before Answering

1. Search local memories when the request depends on the user's preferences, prior decisions, reasoning style, project context, or domain-specific judgment.
2. Use retrieved memories only when they are relevant to the current task.
3. If no relevant memory is found, continue normally and do not pretend to know the user's preference.
4. When memory affects an answer, phrase conclusions as preference-aware judgment, not objective truth.

## Saving Memories

Save only durable, reusable information:

- preference
- decision_rule
- reasoning_pattern
- domain_principle
- anti_pattern
- correction

Do not save one-off task details, transient emotions, secrets, credentials, or sensitive personal data unless the user explicitly asks to save them.

Before saving uncertain or sensitive memories, ask for confirmation. If the user explicitly says "remember", "记住", or "保存这个偏好", saving is confirmed.

Use concise atomic memory text. Include the memory type, scope, confidence, stability, and source in the text or metadata when the available MCP tool supports it.

Preferred schema:

- type: preference | decision_rule | reasoning_pattern | domain_principle | anti_pattern | correction
- scope: applicable domain
- content: one atomic memory
- confidence: low | medium | high
- stability: temporary | evolving | stable
- source: codex

## Conflict Handling

When a new memory conflicts with an old memory:

1. Do not silently overwrite.
2. Explain the conflict.
3. Ask whether to keep both, delete the old one, or save the new one as an updated preference.

## Manual Review

Use `memory_list` and `memory_search` when the user asks to inspect memories. Use `memory_delete` and `memory_delete_all` only for explicit deletion requests.

The local MCP server is stdio-based and backed by local Mem0 storage under:

- `~/.mem0-local/`

No OpenMemory dashboard or HTTP server is required.
