import argparse
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Literal, Optional

os.environ.setdefault("MEM0_TELEMETRY", "false")

from mem0 import Memory
from mem0.configs.embeddings.base import BaseEmbedderConfig
from mem0.embeddings.base import EmbeddingBase
from mem0.utils.factory import EmbedderFactory


DEFAULT_USER_ID = "local-user"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = "deepseek-chat"

# Use "fastembed" for real local embeddings. Use "hash" only when the first
# FastEmbed model download is blocked and you want to smoke-test local storage.
EMBEDDER = "fastembed"
EMBEDDER_MODEL = "BAAI/bge-small-zh-v1.5"
EMBEDDER_DIMS = 512


def _local_dir() -> Path:
    return Path.home() / ".mem0-local"


class LocalHashEmbedding(EmbeddingBase):
    """Small deterministic fallback embedder that needs no model download."""

    def __init__(self, config: Optional[BaseEmbedderConfig] = None):
        super().__init__(config)
        self.config.embedding_dims = self.config.embedding_dims or EMBEDDER_DIMS

    def embed(self, text, memory_action: Optional[Literal["add", "search", "update"]] = None):
        dims = self.config.embedding_dims
        vector = [0.0] * dims
        normalized = " ".join(str(text).lower().split())
        tokens = self._tokens(normalized)
        for token in tokens:
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


def _configure_embedder_factory(embedder_mode: str) -> tuple[str, str]:
    if embedder_mode == "hash":
        EmbedderFactory.provider_to_class["fastembed"] = (
            "examples.local_personal_memory.memory_cli.LocalHashEmbedding"
        )
        return "local-hash", "No model download. Lower semantic quality; useful for bootstrap/smoke tests."
    return EMBEDDER_MODEL, "FastEmbed local ONNX model. First run downloads the model."


def build_memory() -> Memory:
    data_dir = _local_dir()
    qdrant_dir = data_dir / "qdrant"
    history_db_path = data_dir / "history.db"
    qdrant_dir.mkdir(parents=True, exist_ok=True)

    embedder_mode = EMBEDDER.lower()
    embedder_model, _ = _configure_embedder_factory(embedder_mode)
    embedding_dims = int(EMBEDDER_DIMS)
    collection_name = f"personal_memories_{embedding_dims}d_{embedder_mode}"

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
                "embedding_dims": embedding_dims,
            },
        },
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": collection_name,
                "embedding_model_dims": embedding_dims,
                "path": str(qdrant_dir),
                "on_disk": True,
            },
        },
        "history_db_path": str(history_db_path),
    }
    return Memory.from_config(config)


def add_memory(args: argparse.Namespace) -> None:
    memory = build_memory()
    messages = [{"role": "user", "content": args.text}]
    result = memory.add(messages, user_id=args.user_id, infer=not args.no_infer)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def search_memories(args: argparse.Namespace) -> None:
    memory = build_memory()
    results = memory.search(args.query, filters={"user_id": args.user_id}, top_k=args.top_k)
    print(json.dumps(results, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Personal local Mem0 memory using DeepSeek + FastEmbed + Qdrant.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add a memory from text.")
    add_parser.add_argument("text", help="Text to remember.")
    add_parser.add_argument("--user-id", default=DEFAULT_USER_ID, help="Memory namespace.")
    add_parser.add_argument("--no-infer", action="store_true", help="Store text directly without LLM extraction.")
    add_parser.set_defaults(func=add_memory)

    search_parser = subparsers.add_parser("search", help="Search memories.")
    search_parser.add_argument("query", help="Search query.")
    search_parser.add_argument("--user-id", default=DEFAULT_USER_ID, help="Memory namespace.")
    search_parser.add_argument("--top-k", type=int, default=5, help="Maximum number of matches.")
    search_parser.set_defaults(func=search_memories)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
