# Temperature and top_p

## What's actually happening

The model doesn't "think" and write a sentence. It predicts **one token at a time**. After each token it produces a probability distribution over its entire vocabulary — every possible next token gets a score.

For example, after "The sky is":

```
"blue"      → 42%
"clear"     → 18%
"dark"      → 11%
"beautiful" → 8%
"grey"      → 6%
...
```

Temperature controls how that distribution is used to pick the next token.

---

## What temperature does mathematically

- **Temperature = 0.0** — always picks the highest probability token. Fully deterministic. Same input always produces the same output.
- **Temperature < 1.0** — distribution is **sharpened**. High-probability tokens dominate even more; low-probability tokens get crushed toward zero.
- **Temperature = 1.0** — use the distribution as-is.
- **Temperature > 1.0** — distribution is **flattened**. Unlikely tokens become more competitive. Outputs get unpredictable. Most providers cap at 2.0.

Visually:

```
Temperature 0.0     Temperature 0.5     Temperature 1.0     Temperature 1.5
(deterministic)     (focused)           (default)           (creative/chaotic)

"blue"   ████████   "blue"   ███████    "blue"   █████      "blue"   ███
"clear"  ░░░░░░░░   "clear"  ██         "clear"  ███        "clear"  ██
"dark"   ░░░░░░░░   "dark"   █          "dark"   ██         "dark"   ██
"grey"   ░░░░░░░░   "grey"   ░          "grey"   █          "grey"   ██
"vivid"  ░░░░░░░░   "vivid"  ░          "vivid"  █          "vivid"  ██
```

---

## When to use each range

| Range | Use case |
|---|---|
| `0.0` | SQL generation, JSON extraction, code, structured output |
| `0.1–0.3` | Q&A, summarization, factual tasks |
| `0.4–0.7` | Explanations, writing assistance, conversational chat |
| `0.8–1.0` | Brainstorming, generating multiple options, creative writing |
| `> 1.0` | Rarely useful — outputs become incoherent quickly |

---

## The common misconception

Higher temperature ≠ smarter or more creative. It means **more random**.

On a hard reasoning task, temperature 1.0 makes the model *worse* because it introduces randomness into token choices that should be deterministic. Reach for higher temperature only when variety is the explicit goal — not as a way to improve quality.

For most production tasks, **0.0–0.3 is the right default**.

---

## top_p (nucleus sampling)

Temperature has a sibling: `top_p`. Instead of scaling the whole distribution, it cuts off the tail — only tokens that together account for the top P% of probability mass are considered.

- `top_p=1.0` → all tokens considered (default, no cutoff)
- `top_p=0.9` → only tokens making up the top 90% of probability mass

**Don't tune both at the same time.** Pick one and leave the other at its default. Adjusting both simultaneously makes it impossible to reason about what's causing output changes. Most teams fix temperature and leave `top_p=1.0`.
