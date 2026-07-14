import json
import uuid
from types import SimpleNamespace

import pytest

import app.mcp_server as server
from app.models import Memory


class FakeQuery:
    def __init__(self, memories):
        self.memories = memories

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return self.memories


class FakeSession:
    def __init__(self, memories):
        self.memories = memories
        self.added = []

    def query(self, model):
        assert model is Memory
        return FakeQuery(self.memories)

    def add(self, value):
        self.added.append(value)

    def commit(self):
        pass

    def close(self):
        pass


class FakeVectorStore:
    def __init__(self, hits):
        self.hits = hits
        self.calls = []

    def search(self, **kwargs):
        self.calls.append(kwargs)
        return self.hits


class FakeMemoryClient:
    def __init__(self, hits):
        self.embedding_model = SimpleNamespace(
            embed=lambda query, mode: [0.1, 0.2]
        )
        self.vector_store = FakeVectorStore(hits)


def make_memory(memory_id):
    return SimpleNamespace(id=uuid.UUID(memory_id))


def make_hit(
    memory_id,
    score,
    scope,
    memory_type="narrative-rule",
    domain="narrative-logic",
):
    return SimpleNamespace(
        id=memory_id,
        score=score,
        payload={
            "data": f"memory {memory_id}",
            "hash": memory_id.replace("-", ""),
            "scope": scope,
            "type": memory_type,
            "domain": domain,
        },
    )


def install_search_fakes(monkeypatch, memories, hits, accessible=True):
    session = FakeSession(memories)
    client = FakeMemoryClient(hits)
    monkeypatch.setattr(server, "SessionLocal", lambda: session)
    monkeypatch.setattr(server, "get_memory_client_safe", lambda: client)
    monkeypatch.setattr(
        server,
        "get_user_and_app",
        lambda db, user_id, app_id: (
            SimpleNamespace(id=uuid.uuid4()),
            SimpleNamespace(id=uuid.uuid4()),
        ),
    )
    monkeypatch.setattr(
        server,
        "check_memory_access_permissions",
        lambda db, memory, app_id: accessible,
    )
    return session, client


def test_extract_memory_metadata():
    text = """Rule.

metadata:
type: narrative-rule
scope: project:midnights-children-reference
domain: narrative-logic
"""
    assert server._extract_memory_metadata(text) == {
        "type": "narrative-rule",
        "scope": "project:midnights-children-reference",
        "domain": "narrative-logic",
    }


def test_scope_is_inferred_from_query():
    assert server._resolve_search_scope(
        "project:midnights-children-reference 人物动机",
        None,
    ) == "project:midnights-children-reference"
    assert server._resolve_search_scope(
        "anything", " project:explicit "
    ) == "project:explicit"
    assert server._resolve_search_scope(
        "project:vlab-frontend:architecture package boundary",
        None,
    ) == "project:vlab-frontend:architecture"


@pytest.mark.asyncio
async def test_search_hard_filters_scope_limit_and_score(monkeypatch):
    current_id = "11111111-1111-4111-8111-111111111111"
    weak_id = "22222222-2222-4222-8222-222222222222"
    other_id = "33333333-3333-4333-8333-333333333333"
    memories = [
        make_memory(current_id),
        make_memory(weak_id),
        make_memory(other_id),
    ]
    hits = [
        make_hit(other_id, 0.99, "project:vlab-frontend"),
        make_hit(current_id, 0.80, "project:midnights-children-reference"),
        make_hit(weak_id, 0.40, "project:midnights-children-reference"),
    ]
    _, client = install_search_fakes(monkeypatch, memories, hits)

    user_token = server.user_id_var.set("me")
    client_token = server.client_name_var.set("codex")
    try:
        raw = await server.search_memory(
            "project:midnights-children-reference 人物动机",
            limit=3,
            min_score=0.45,
        )
    finally:
        server.user_id_var.reset(user_token)
        server.client_name_var.reset(client_token)

    result = json.loads(raw)
    assert [item["id"] for item in result["results"]] == [current_id]
    call = client.vector_store.calls[0]
    assert call["filters"] == {
        "user_id": "me",
        "scope": "project:midnights-children-reference",
    }
    assert call["top_k"] == 10


@pytest.mark.asyncio
async def test_search_returns_empty_when_acl_allows_nothing(monkeypatch):
    memory_id = "11111111-1111-4111-8111-111111111111"
    memories = [make_memory(memory_id)]
    _, client = install_search_fakes(
        monkeypatch,
        memories,
        [make_hit(
            memory_id,
            0.9,
            "project:midnights-children-reference",
        )],
        accessible=False,
    )

    user_token = server.user_id_var.set("me")
    client_token = server.client_name_var.set("codex")
    try:
        raw = await server.search_memory(
            "project:midnights-children-reference test"
        )
    finally:
        server.user_id_var.reset(user_token)
        server.client_name_var.reset(client_token)

    assert json.loads(raw) == {"results": []}
    assert client.vector_store.calls == []
