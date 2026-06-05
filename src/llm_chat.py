import os
import time
import argparse
from dotenv import load_dotenv

load_dotenv()

# Cost per 1000 tokens in USD. Groq open-access models are free.
PRICING = {
    "llama-3.3-70b-versatile":  {"input": 0.0,    "output": 0.0},
    "llama-3.1-8b-instant":     {"input": 0.0,    "output": 0.0},
    "claude-haiku-4-5":         {"input": 0.0008, "output": 0.004},
    "claude-sonnet-4-5":        {"input": 0.003,  "output": 0.015},
}

DEFAULT_SYSTEM = "You are a helpful financial analyst specialising in Indian equities."


def _cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = PRICING.get(model, {"input": 0.0, "output": 0.0})
    return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1000


def _call_groq(prompt: str, system: str, temperature: float, model: str) -> dict:
    from groq import Groq

    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    start = time.time()
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
    )
    latency_ms = int((time.time() - start) * 1000)

    input_tokens  = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens

    return {
        "response":      response.choices[0].message.content,
        "input_tokens":  input_tokens,
        "output_tokens": output_tokens,
        "cost_usd":      _cost(model, input_tokens, output_tokens),
        "model":         model,
        "provider":      "groq",
        "latency_ms":    latency_ms,
    }


def _call_anthropic(prompt: str, system: str, temperature: float, model: str) -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    start = time.time()
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        temperature=temperature,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    latency_ms = int((time.time() - start) * 1000)

    input_tokens  = response.usage.input_tokens
    output_tokens = response.usage.output_tokens

    return {
        "response":      response.content[0].text,
        "input_tokens":  input_tokens,
        "output_tokens": output_tokens,
        "cost_usd":      _cost(model, input_tokens, output_tokens),
        "model":         model,
        "provider":      "anthropic",
        "latency_ms":    latency_ms,
    }


def chat(
    prompt: str,
    system: str = DEFAULT_SYSTEM,
    temperature: float = 0.1,
    model: str = None,
    provider: str = None,
) -> dict:
    """
    Send a prompt to an LLM and return the response with token usage and cost.

    Returns:
        {
            "response":      str,
            "input_tokens":  int,
            "output_tokens": int,
            "cost_usd":      float,
            "model":         str,
            "provider":      str,
            "latency_ms":    int,
        }
    """
    provider = provider or os.getenv("LLM_PROVIDER", "groq")
    model    = model    or os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

    if provider == "groq":
        return _call_groq(prompt, system, temperature, model)
    elif provider == "anthropic":
        return _call_anthropic(prompt, system, temperature, model)
    else:
        raise ValueError(f"Unknown provider '{provider}'. Supported: groq, anthropic")


def _print_result(result: dict) -> None:
    print(result["response"])
    print(f"\n[{result['provider']} / {result['model']}]")
    print(f"Tokens : {result['input_tokens']} in / {result['output_tokens']} out")
    print(f"Cost   : ${result['cost_usd']:.6f}  |  Latency: {result['latency_ms']}ms")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chat with an LLM from the command line.")
    parser.add_argument("prompt",                              help="The prompt to send")
    parser.add_argument("--system",      default=DEFAULT_SYSTEM, help="System prompt")
    parser.add_argument("--temperature", type=float, default=0.1, help="Sampling temperature")
    parser.add_argument("--model",       default=None,         help="Model name (overrides LLM_MODEL env var)")
    parser.add_argument("--provider",    default=None,         help="Provider: groq | anthropic")
    args = parser.parse_args()

    result = chat(args.prompt, args.system, args.temperature, args.model, args.provider)
    _print_result(result)
