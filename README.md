# GenAI Learning Path

A hands-on implementation of [The GenAI Learning Path](https://www.incontext.sh/learning/genai) by In Context.

One evolving Python codebase built across 11 phases — from a raw LLM API call to a production-minded multi-agent system.

## Learning Roadmap

For the fundamentals-first path covering neural networks, LLM internals, Transformers, training, RAG and retrieval alternatives, production AI, and Forward-Deployed Engineering, see:

- [AI Foundations to Forward-Deployed AI Engineer](docs/AI-FOUNDATIONS-LEARNING-PATH.md)

## Phases

| # | Topic | Artifact |
|---|-------|----------|
| 01 | Talk to an LLM | `src/llm_chat.py` |
| 02 | RAG over your documents | `src/rag.py` |
| 03 | Systematic evaluation | `evals/promptfooconfig.yaml` |
| 04 | Tool-using agent | `src/agent.py` |
| 05 | Observability & cost | `notebooks/traces.ipynb` |
| 06 | Guardrails & safety | `src/guardrails.py` |
| 07 | Cross-session memory | `src/memory.py` |
| 08 | MCP tool standardization | `mcp/sql_mcp_server/` |
| 09 | Agent-level CI evals | `evals/agent_evals/` |
| 10 | Multi-agent orchestration | `src/swarm.py` |
| 11 | Harness & production runtime | `harness.md` |

## Setup

```bash
cp .env.example .env   # add your API keys
pip install -r requirements.txt
```

### Phase 03 — run eval

Requires Phase 02 index built (`python src/rag.py --index`) and [Promptfoo installed](docs/PHASE-NOTES/phase-03/setup.md).

```bash
./evals/run_eval.sh
promptfoo view
```

See [docs/PHASE-NOTES/phase-03/](docs/PHASE-NOTES/phase-03/) for concepts, walkthrough, and baseline results.

## Reference

- Full requirements and design decisions: [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md)
- Fundamentals and FDE learning roadmap: [docs/AI-FOUNDATIONS-LEARNING-PATH.md](docs/AI-FOUNDATIONS-LEARNING-PATH.md)
