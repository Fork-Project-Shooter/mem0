import hashlib
import math
import os
from pathlib import Path
from typing import Any, Dict, Literal, Optional

os.environ.setdefault("MEM0_TELEMETRY", "false")

from mem0 import Memory
from mem0.configs.embeddings.base import BaseEmbedderConfig
from mem0.embeddings.base import EmbeddingBase
from mem0.utils.factory import EmbedderFactory


DEFAULT_USER_ID = "me"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = "deepseek-chat"

# Use "fastembed" for real local embeddings. Use "hash" only when FastEmbed
# model download is blocked and you want to smoke-test local storage.
EMBEDDER = "fastembed"
EMBEDDER_MODEL = "BAAI/bge-small-zh-v1.5"
EMBEDDER_DIMS = 512


class LocalHashEmbedding(EmbeddingBase):
    """Deterministic fallback embedder that needs no model download."""

    def __init__(self, config: Optional[BaseEmbedderConfig] = None):
        super().__init__(config)
        self.config.embedding_dims = self.config.embedding_dims or EMBEDDER_DIMS

    def embed(self, text, memory_action: Optional[Literal["add", "search", "update"]] = None):
        dims = self.config.embedding_dims
        vector = [0.0] * dims
        normalized = " ".join(str(text).lower().split())
        for token in self._tokens(normalized):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "little") % dims
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector

    @staticmethod
    def _tokens(text: str) -> list[str]:
        if not text:
            return []
        tokens = [part for part in text.split(" ") if part]
        chars = [char for char in text if not char.isspace()]
        tokens.extend(chars)
        tokens.extend(text[index : index + 2] for index in range(max(len(text) - 1, 0)))
        return tokens


class LocalMem0Adapter:
    def __init__(self):
        self._memory: Memory | None = None

    @property
    def storage_dir(self) -> Path:
        return Path.home() / ".mem0-local"

    def _configure_embedder_factory(self, embedder_mode: str) -> str:
        if embedder_mode == "hash":
            EmbedderFactory.provider_to_class["fastembed"] = "mem0_adapter.LocalHashEmbedding"
            return "local-hash"
        return EMBEDDER_MODEL

    def _client(self) -> Memory:
        if self._memory is not None:
            return self._memory

        qdrant_dir = self.storage_dir / "qdrant"
        history_db_path = self.storage_dir / "history.db"
        qdrant_dir.mkdir(parents=True, exist_ok=True)

        embedder_mode = EMBEDDER.lower()
        embedder_model = self._configure_embedder_factory(embedder_mode)
        collection_name = f"personal_memories_{EMBEDDER_DIMS}d_{embedder_mode}"

        config = {
            "version": "v1.1",
            "llm": {
                "provider": "deepseek",
                "config": {
                    "api_key": DEEPSEEK_API_KEY,
                    "model": DEEPSEEK_MODEL,
                    "temperature": 0.2,
                    "max_tokens": 2000,
                    "top_p": 1.0,
                },
            },
            "embedder": {
                "provider": "fastembed",
                "config": {
                    "model": EMBEDDER_MODEL if embedder_mode != "hash" else embedder_model,
                    "embedding_dims": EMBEDDER_DIMS,
                },
            },
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "collection_name": collection_name,
                    "embedding_model_dims": EMBEDDER_DIMS,
                    "path": str(qdrant_dir),
                    "on_disk": True,
                },
            },
            "history_db_path": str(history_db_path),
        }
        self._memory = Memory.from_config(config)
        return self._memory

    def add(
        self,
        content: str,
        user_id: str = DEFAULT_USER_ID,
        memory_type: str = "preference",
        scope: str = "general",
        confidence: str = "medium",
        stability: str = "stable",
        metadata: Optional[Dict[str, Any]] = None,
        infer: bool = True,
    ):
        merged_metadata = {
            "type": memory_type,
            "scope": scope,
            "confidence": confidence,
            "stability": stability,
            "source": "codex",
            **(metadata or {}),
        }
        return self._client().add(
            [{"role": "user", "content": content}],
            user_id=user_id,
            metadata=merged_metadata,
            infer=infer,
        )

    def search(self, query: str, user_id: str = DEFAULT_USER_ID, scope: Optional[str] = None, limit: int = 5):
        filters: Dict[str, Any] = {"user_id": user_id}
        if scope:
            filters["scope"] = scope
        return self._client().search(query, filters=filters, top_k=limit)

    def list(self, user_id: str = DEFAULT_USER_ID, scope: Optional[str] = None, limit: int = 50):
        filters: Dict[str, Any] = {"user_id": user_id}
        if scope:
            filters["scope"] = scope
        return self._client().get_all(filters=filters, top_k=limit)

    def get(self, memory_id: str):
        return self._client().get(memory_id)

    def update(self, memory_id: str, content: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        return self._client().update(memory_id, data=content, metadata=metadata)

    def delete(self, memory_id: str):
        return self._client().delete(memory_id)

    def delete_all(self, user_id: str = DEFAULT_USER_ID):
        return self._client().delete_all(user_id=user_id)

    def health(self):
        return {
            "status": "ok",
            "storage_dir": str(self.storage_dir),
            "user_id": DEFAULT_USER_ID,
            "llm": {
                "provider": "deepseek",
                "model": DEEPSEEK_MODEL,
                "api_key_set": bool(DEEPSEEK_API_KEY),
            },
            "embedder": {"mode": EMBEDDER, "model": EMBEDDER_MODEL, "dims": EMBEDDER_DIMS},
        }
