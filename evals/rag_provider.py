"""
Promptfoo Python provider — wraps rag.query() for Phase 03 evals.

Called by Promptfoo with:
  prompt   — rendered prompt string ({{question}} from test vars)
  options  — provider config from promptfooconfig.yaml
  context  — test vars and metadata
"""

import json
import sys
from pathlib import Path

# Project root (parent of evals/) on path for rag + llm_chat imports
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from rag import query  # noqa: E402


def call_api(prompt: str, options: dict, context: dict) -> dict:
    config = options.get("config", {})
    vars_ = context.get("vars", {})

    # Prefer explicit test var; fall back to rendered prompt
    question = vars_.get("question") or prompt
    if isinstance(question, str):
        question = question.strip()
    else:
        question = str(question)

    top_k = int(config.get("top_k", 5))
    index_dir = config.get("index_dir", "data/index")
    provider = config.get("provider")
    model = config.get("model")

    try:
        result = query(
            question=question,
            index_dir=str(ROOT / index_dir),
            top_k=top_k,
            provider=provider,
            model=model,
        )
    except Exception as exc:
        return {"error": str(exc)}

    # Append source summary so eval output shows retrieval context
    source_lines = [
        f"[{s['score']:.3f}] {s['source']} p.{s['page']}"
        for s in result.get("sources", [])
    ]
    output = result["answer"]
    if source_lines:
        output += "\n\n--- sources ---\n" + "\n".join(source_lines)

    in_tok = result.get("input_tokens", 0)
    out_tok = result.get("output_tokens", 0)

    return {
        "output": output,
        "tokenUsage": {
            "total": in_tok + out_tok,
            "prompt": in_tok,
            "completion": out_tok,
        },
        "cost": result.get("cost_usd", 0.0),
        "latencyMs": result.get("latency_ms", 0),
        # Available to javascript assertions if needed later
        "metadata": {
            "sources": result.get("sources", []),
            "raw_answer": result["answer"],
        },
    }


# Quick manual test: python evals/rag_provider.py
if __name__ == "__main__":
    sample = call_api(
        "Who is the CEO of Infosys?",
        {"config": {"top_k": 5}},
        {"vars": {"question": "Who is the CEO of Infosys?"}},
    )
    print(json.dumps(sample, indent=2))
