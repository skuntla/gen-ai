# Questions — Phase 01

These cover concepts, design decisions, and implementation details from Phase 01.
Use for interview prep, self-testing, and teaching.

---

## Concepts

**Q: What is an LLM from an engineering perspective?**
An HTTP API. You send a JSON payload with a messages array, you get a JSON response back. The model runs on the provider's servers — you are making web requests.

**Q: What is the messages format and why is it universal?**
Every major provider (Anthropic, OpenAI, Groq/Meta) uses the same structure: a `system` message that sets persona and rules, followed by alternating `user` and `assistant` turns. It's universal because it maps directly to how a conversation works — context first, then exchange.

**Q: What is a token?**
A chunk of characters, roughly 3–4 characters or ~0.75 words. Not the same as a word. You pay per token (input and output billed separately). The model's context window is also measured in tokens.

**Q: Why are LLMs stateless?**
Each API call is independent. The model has no memory of previous calls. If you want conversation history, you must include prior messages in the `messages` array yourself. This constraint is why Phase 07 (Memory) exists.

**Q: What is the system prompt and why does it matter?**
The `system` message is processed before the user's input. It controls tone, format, persona, and constraints. Most production quality issues trace back to a poorly written system prompt. It is a first-class engineering artifact.

**Q: What are the three main knobs you can tune in an LLM API call?**
Model selection (quality vs cost vs speed), system prompt (behaviour and format), and temperature (randomness of token selection).

---

## Temperature and sampling

**Q: What does temperature actually control?**
The probability distribution over possible next tokens. At 0.0 the model always picks the highest-probability token (deterministic). Below 1.0 the distribution is sharpened — high-probability tokens dominate more. Above 1.0 the distribution is flattened — unlikely tokens become more competitive.

**Q: Higher temperature means smarter output — true or false?**
False. Higher temperature means more random. On reasoning tasks it makes the model worse. Use higher temperature only when variety is the explicit goal (brainstorming, creative writing).

**Q: What is top_p and how does it differ from temperature?**
`top_p` cuts off the tail of the distribution — only tokens accounting for the top P% of probability mass are considered. Temperature scales the whole distribution. Don't tune both at the same time; pick one and leave the other at its default.

**Q: What temperature would you use for SQL generation vs brainstorming?**
SQL generation: `0.0` — you want the same correct answer every time. Brainstorming: `0.8–1.0` — variety is the point.

---

## Design decisions

**Q: Why does `chat()` return a dict instead of just a string?**
Because every caller needs more than the text response — they need token counts, cost, latency, model, and provider. Returning just a string would force every caller to duplicate the logging and cost logic.

**Q: Why are `_call_groq` and `_call_anthropic` prefixed with an underscore?**
Single underscore is a Python convention meaning "private — internal implementation detail, not part of the public interface." It signals that callers should use `chat()`, not these functions directly. If a provider is swapped out later, only the internals change — nothing that calls `chat()` breaks.

**Q: Why is the model name read from an environment variable instead of hardcoded?**
Because the model you use today will not be the model you use in six months. If it's hardcoded, every model change is a code change, a PR, and a deployment. If it's in config, it's a one-line `.env` change with no code touched.

**Q: What is the provider abstraction and why does it exist?**
`llm_chat.py` routes API calls to different SDKs (Groq, Anthropic) based on the `LLM_PROVIDER` environment variable. The public `chat()` function always returns the same dict shape regardless of which provider is underneath. This means all future phases call `chat()` identically — swapping providers is invisible to them.

**Q: Why is `llm_chat.py` written as a module with a callable function, not just a script?**
Because Phase 04 (Agent) imports and calls `chat()` directly. If it were only a script, every phase would have to subprocess-call it or duplicate the logic. A clean function API makes it a reusable building block.

**Q: Why log cost even though Groq is free?**
Building the habit now means you don't retrofit it when you switch to a paid provider. The cost formula is the same regardless — `(input_tokens × price + output_tokens × price) / 1000`. Groq's price is simply 0.0.

---

## Broader / interview-level

**Q: What is the difference between a workflow and an agent?**
In a workflow, you (the developer) decide the sequence of steps. In an agent, the LLM decides which actions to take and in what order. Phase 01 is a workflow — we call the LLM once with a fixed prompt. Phase 04 introduces the agent loop.

**Q: If the same prompt gives different outputs each time, what would you change?**
Lower the temperature toward 0.0. At 0.0 the output is deterministic — the same input always produces the same output.

**Q: A colleague says "just use GPT-4 for everything." What's the problem with that?**
Cost and latency. Frontier models cost 10–20x more per token than small models and respond slower. Most tasks don't need frontier-level reasoning. The right approach is to use the smallest model that produces acceptable quality for each specific task.

**Q: What happens to cost as conversation history grows?**
It increases linearly. Every prior turn you include in the messages array adds to the input token count, and you pay for all of it on every call. This is why context compaction (Phase 07) matters — you can't just keep appending history forever.
