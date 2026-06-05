# Local Models with Ollama

Running models locally means zero API cost, full privacy, and offline capability.
Ollama is the easiest way to run local models on macOS — it handles downloads, quantization, and serves a local HTTP API.

---

## Installation

```bash
brew install ollama
```

Start the server (runs on `http://localhost:11434`):
```bash
ollama serve
```

> On macOS, Ollama can also run as a menu bar app. Either way works.

---

## Choosing a model

Pick based on your available RAM and disk space. Ollama downloads Q4 quantized models by default.

| Model | Pull command | Disk | RAM needed | Quality | Best for |
|---|---|---|---|---|---|
| `llama3.2:3b` | `ollama pull llama3.2` | ~2 GB | ~3 GB | Decent | Fast testing, low-resource machines |
| `llama3.1:8b` | `ollama pull llama3.1:8b` | ~5 GB | ~6 GB | Good | General purpose, recommended default |
| `mistral:7b` | `ollama pull mistral` | ~4 GB | ~5 GB | Good | General purpose, strong on structured output |
| `phi4-mini` | `ollama pull phi4-mini` | ~3 GB | ~4 GB | Good | Reasoning tasks, small footprint |
| `llama3.1:70b` | `ollama pull llama3.1:70b` | ~40 GB | ~42 GB | Very good | Near-frontier, needs 48GB+ RAM |

**All models listed above are free and open-source.**

### Quick decision guide

| Your free RAM | Recommended model |
|---|---|
| 8 GB | `llama3.2:3b` |
| 16 GB | `llama3.1:8b` or `mistral:7b` |
| 24 GB | `llama3.1:8b` (comfortable headroom) |
| 48 GB+ | `llama3.1:70b` |

> macOS and running apps use 4–8 GB RAM on top of the model. Factor that in.

---

## What quantization means

Models are stored in different precision formats. Ollama defaults to Q4 (4-bit quantized):

| Format | Quality | Size vs full |
|---|---|---|
| FP16 (full) | Best | 1x (e.g. 16 GB for 8B model) |
| Q8 | Near-identical | ~0.5x |
| Q4 (default) | Slight drop | ~0.25x |
| Q2 | Noticeable drop | ~0.12x |

For this learning path, Q4 is the right default — good enough quality, fits comfortably in RAM.

---

## Verify the model is running

After `ollama serve` and `ollama pull <model>`, test it:

```bash
ollama run llama3.1:8b "What is the P/E ratio of a stock?"
```

Or via the API directly:
```bash
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1:8b",
    "messages": [{"role": "user", "content": "What is a P/E ratio?"}]
  }'
```

---

## Using Ollama in this project

Ollama exposes an OpenAI-compatible API, so `llm_chat.py` supports it as a provider.

Add to `.env`:
```
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:8b
OLLAMA_BASE_URL=http://localhost:11434/v1
```

Then run exactly as normal:
```bash
python src/llm_chat.py "Analyse Infosys as an investment"
```

No API key needed for Ollama. Cost is always `$0.000000`.

> Ollama must be running (`ollama serve`) before calling `llm_chat.py` with `LLM_PROVIDER=ollama`.

---

## Apple Silicon note (M1/M2/M3/M4)

Ollama uses Metal GPU acceleration automatically on Apple Silicon. Unified memory means RAM and GPU share the same pool — a 24 GB M4 can run `llama3.1:8b` entirely on-chip with fast inference (~30–50 tokens/second). No special configuration needed.

---

## Useful Ollama commands

```bash
ollama list              # show downloaded models
ollama pull llama3.1:8b  # download a model
ollama rm llama3.2       # delete a model (frees disk space)
ollama ps                # show currently running models
ollama show llama3.1:8b  # show model details and parameters
```
