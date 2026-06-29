# Local Personal Memory

This example runs Mem0 as a personal local library:

- DeepSeek is used only as the LLM.
- FastEmbed runs Chinese-friendly embeddings locally on CPU.
- Qdrant embedded mode stores vectors on local disk.
- No REST server, dashboard, admin user, JWT, or Docker is required.

## Install

From the repository root:

```powershell
python -m pip install -e ".[extras]"
```

If `python` points to the Microsoft Store stub, install Python 3.10-3.12 first and rerun the command with that Python.

## Configure

Edit the constants at the top of `memory_cli.py`:

```python
DEEPSEEK_API_KEY = "your-deepseek-api-key"
EMBEDDER = "fastembed"
```

The default local embedder is `BAAI/bge-small-zh-v1.5` with 512 dimensions. FastEmbed downloads this model the first time you run the script, then reuses the local cache. If your network cannot reach Hugging Face or the Qdrant mirror, download/configure the model cache first or switch to another local embedder such as Ollama.

If you are behind a network that cannot reach Hugging Face directly, set a compatible Hugging Face endpoint before the first run:

```powershell
$env:HF_ENDPOINT="https://hf-mirror.com"
```

## Use

### Bootstrap Without Model Download

Use this first to verify the local vector store and CLI are working:

```powershell
python examples/local_personal_memory/memory_cli.py add "我喜欢科幻电影，不太喜欢惊悚片" --no-infer
python examples/local_personal_memory/memory_cli.py search "我喜欢什么电影？"
```

To avoid any embedding model download during bootstrap, set this at the top of `memory_cli.py`:

```python
EMBEDDER = "hash"
```

`hash` mode is only a bootstrap/smoke-test fallback; use FastEmbed or Ollama for real semantic retrieval.

Return to FastEmbed after using hash mode by setting:

```python
EMBEDDER = "fastembed"
```

### Real Local Memory

Add a memory:

```powershell
python examples/local_personal_memory/memory_cli.py add "我喜欢科幻电影，不太喜欢惊悚片"
```

Search memories:

```powershell
python examples/local_personal_memory/memory_cli.py search "我喜欢什么电影？"
```

Use another user id:

```powershell
python examples/local_personal_memory/memory_cli.py add "我每天早上喝黑咖啡" --user-id alice
python examples/local_personal_memory/memory_cli.py search "早餐习惯" --user-id alice
```

## Local Data

By default data is stored under:

```text
~/.mem0-local/
```

Changing the embedder model later requires rebuilding existing memories because old and new vectors are not comparable.
