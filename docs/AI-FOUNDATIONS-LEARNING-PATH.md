# AI Foundations to Forward-Deployed AI Engineer

A fundamentals-first, project-driven learning path for understanding how modern AI systems work internally and learning to design, evaluate, secure, and deploy them in enterprise environments.

This roadmap complements the repository's existing 11-phase GenAI application path. The existing phases teach how to build increasingly capable applications; this document adds the deeper model, retrieval, systems, and forward-deployment foundations needed to reason about those applications confidently.

---

## 1. Goal

The objective is not to become a foundation-model researcher or memorize every new framework.

The objective is to become an engineer who can:

- Explain how neural networks and language models learn.
- Understand the major tensor operations inside a Transformer.
- Build and train a small GPT-style model.
- Distinguish model parameters, token embeddings, document embeddings, context, memory, and external tools.
- Build retrieval systems without depending entirely on a high-level framework.
- Compare RAG, long-context, hierarchical retrieval, SQL, APIs, and tool-based approaches.
- Create representative evaluation datasets and diagnose failures.
- Design production systems with security, observability, reliability, and human approval.
- Translate ambiguous enterprise problems into measurable AI solutions.
- Present credible portfolio evidence for Applied AI and Forward-Deployed Engineering roles.

### Recommended learning balance

- **30% model fundamentals and internals**
- **70% building, evaluating, deploying, and communicating real systems**

Understanding the internals is essential. However, the market value comes from using that understanding to make better engineering and business decisions.

---

## 2. Durable concepts to master

Tools and model names will change. These concepts will remain useful.

### Mathematical and learning foundations

- Scalars, vectors, matrices, tensors
- Dot products and matrix multiplication
- Probability distributions and softmax
- Loss functions and cross-entropy
- Gradients, chain rule, and backpropagation
- Optimization and learning rates
- Training, validation, and test sets
- Generalization, overfitting, and regularization

### Language-model foundations

- Tokenization and vocabulary construction
- Token embeddings and contextual hidden states
- Positional information
- Self-attention and multi-head attention
- Feed-forward networks
- Residual connections and normalization
- Transformer blocks
- Autoregressive next-token prediction
- Pretraining, instruction tuning, preference optimization, and fine-tuning
- Decoding, temperature, top-k, and top-p sampling
- Inference memory, KV cache, latency, and throughput

### Knowledge and context foundations

- Sparse retrieval and inverted indexes
- BM25 and keyword search
- Dense embeddings and vector similarity
- Approximate nearest-neighbor search
- Metadata filtering and access control
- Reranking
- Hybrid retrieval
- Hierarchical retrieval and summary indexes
- Full-document and long-context approaches
- Structured retrieval through SQL and APIs
- Context construction, compression, and citation

### Production and FDE foundations

- Problem discovery and workflow mapping
- Acceptance criteria and business metrics
- APIs, databases, queues, and state
- Structured outputs and tool contracts
- Evaluation and regression testing
- Reliability, retries, idempotency, and fallbacks
- Authentication, authorization, least privilege, and auditability
- Prompt-injection and tool-abuse defenses
- Observability, tracing, cost, and latency
- Human-in-the-loop design
- Adoption, trust, and measurable business impact

---

## 3. How to study each concept

Use the same six-step loop throughout the roadmap:

1. **Understand the intuition.** Explain the concept without equations.
2. **Learn the minimum mathematics.** Understand what the computation means.
3. **Implement a small version.** Avoid high-level abstractions initially.
4. **Use the production library.** Learn the practical ecosystem after the internals.
5. **Break it deliberately.** Create edge cases and inspect failure behavior.
6. **Explain the trade-offs.** Document when to use it and when not to use it.

For every module, try to produce:

```text
concept.md
math.md
implementation.py
experiment.ipynb
failure-modes.md
interview-questions.md
```

---

# 4. Sixteen-week learning roadmap

Assumption: approximately **8–10 focused hours per week**.

The schedule can be extended. Completion should be based on deliverables and understanding, not calendar speed.

---

## Phase 1 — Neural-network foundations

**Weeks 1–2**

### Learn

- Parameters versus activations
- Forward pass and computational graphs
- Derivatives and the chain rule
- Gradients and backpropagation
- Gradient descent
- Common activation functions
- Loss functions
- Training versus inference
- Training, validation, and test data
- Overfitting and generalization

### Build

1. A tiny scalar automatic-differentiation engine.
2. A small multilayer perceptron.
3. A model that learns XOR or a simple classification dataset.

Example target API:

```python
x = Value(2.0)
y = Value(3.0)
z = x * y + x
z.backward()
```

### Evidence of mastery

You should be able to explain:

- What a gradient represents.
- Why backpropagation uses the chain rule.
- Which values change during training.
- Why inference does not normally update model weights.
- How learning rate affects convergence.

### Primary resources

- [Andrej Karpathy — Neural Networks: Zero to Hero](https://karpathy.ai/zero-to-hero.html)
- [Dive into Deep Learning](https://en.d2l.ai/)
- [PyTorch Tutorials](https://docs.pytorch.org/tutorials/)

### Repository artifact

```text
foundations/01-autograd/
foundations/02-neural-networks/
```

---

## Phase 2 — Tokenization and language modeling

**Weeks 3–4**

### Learn

- Character, word, byte, and subword tokenization
- Vocabulary size and sequence length trade-offs
- Byte-pair encoding
- Token IDs
- Embedding lookup tables
- Autoregressive language modeling
- Input and target sequence shifting
- Cross-entropy loss
- Perplexity
- Context length

### Build

1. A character tokenizer.
2. A small subword tokenizer or simplified BPE implementation.
3. A bigram language model.
4. A simple text-generation loop.

### Experiments

Compare character, word, and subword tokenization on:

- Vocabulary size
- Sequence length
- Unknown words
- Compression
- Training speed
- Generated output quality

### Evidence of mastery

You should be able to clearly distinguish:

- A token ID
- A token embedding
- A contextual hidden state
- A document embedding
- A model parameter

### Primary resources

- [Hugging Face LLM Course](https://huggingface.co/learn/llm-course/en/chapter1/1)
- [Build a Large Language Model From Scratch](https://sebastianraschka.com/llms-from-scratch/)
- Karpathy's Zero to Hero language-model lectures

### Repository artifact

```text
foundations/03-tokenization/
foundations/04-language-modeling/
```

---

## Phase 3 — Attention and Transformers

**Weeks 5–7**

### Learn

- Why earlier sequence models were difficult to parallelize
- Query, key, and value projections
- Scaled dot-product attention
- Causal masking
- Self-attention
- Multi-head attention
- Positional embeddings or encodings
- Feed-forward networks
- Residual connections
- Layer normalization
- Transformer blocks
- Encoder-only, encoder-decoder, and decoder-only architectures

### Build

1. One attention head using basic PyTorch tensor operations.
2. Multi-head attention.
3. A Transformer block.
4. A decoder-only mini-GPT architecture.

Core computation:

```python
scores = queries @ keys.transpose(-2, -1)
scores = scores / math.sqrt(head_dimension)
scores = scores.masked_fill(causal_mask == 0, float("-inf"))
weights = torch.softmax(scores, dim=-1)
output = weights @ values
```

### Tensor-shape exercise

Given:

```text
Batch size       B = 4
Sequence length  T = 128
Embedding size   D = 256
Attention heads  H = 8
Head dimension   = 32
```

Be able to explain:

```text
Input tokens      [B, T]
Embeddings        [B, T, D]
Queries           [B, H, T, 32]
Keys              [B, H, T, 32]
Attention scores  [B, H, T, T]
Values            [B, H, T, 32]
Output            [B, T, D]
Logits            [B, T, vocabulary_size]
```

### Evidence of mastery

You should be able to explain:

- What attention does and does not do.
- Why causal masking is required for autoregressive generation.
- Why attention memory grows quickly with sequence length.
- Why multiple heads can learn different relationships.
- How attention differs from external retrieval.

### Primary resources

- [Attention Is All You Need](https://arxiv.org/abs/1706.03762) — read after implementing attention once
- [Dive into Deep Learning — Attention and Transformers](https://d2l.ai/chapter_attention-mechanisms-and-transformers/index.html)
- [Build a Large Language Model From Scratch](https://sebastianraschka.com/llms-from-scratch/)

### Repository artifact

```text
foundations/05-self-attention/
foundations/06-transformer/
```

---

## Phase 4 — Train a small GPT

**Weeks 8–9**

### Learn

- Dataset preparation
- Mini-batches
- Weight initialization
- Optimizers and AdamW
- Learning-rate schedules
- Training loops
- Validation loss
- Checkpointing
- Sampling and decoding
- Temperature, top-k, and top-p
- Repetition and degeneration
- Model size, data, and compute trade-offs

### Build

Train a small GPT-style model on one of:

- Shakespeare
- Public-domain text
- A small technical corpus
- Sanitized financial or corporate-action text

This model is educational, not a commercial foundation model.

### Required observations

Document:

- Where the parameters live.
- What changes during training.
- What remains fixed during inference.
- Why validation loss may diverge from training loss.
- How generation quality changes with temperature.
- Why small models repeat or lose coherence.

### Primary resources

- [Build a Large Language Model From Scratch](https://sebastianraschka.com/llms-from-scratch/)
- [Stanford CS336 — Language Modeling From Scratch](https://cs336.stanford.edu/) — use selected lectures after the smaller implementation
- Karpathy's GPT implementation lectures

### Repository artifact

```text
foundations/07-mini-gpt/
foundations/08-training-and-generation/
```

---

## Phase 5 — Post-training and model adaptation

**Weeks 10–11**

### Learn

- Pretraining versus instruction tuning
- Supervised fine-tuning
- Preference optimization
- Reinforcement learning concepts for LLMs
- Fine-tuning versus prompting
- LoRA and QLoRA
- Quantization
- Distillation
- Tool-use training
- Structured-output behavior

### Build

Use a small pretrained open model for a focused structured-extraction experiment.

Example task:

```json
{
  "event_type": "cash_dividend",
  "amount": 1.25,
  "currency": "USD",
  "record_date": "2026-08-15"
}
```

Compare:

1. Prompt only
2. Few-shot prompting
3. Prompt plus schema validation
4. Parameter-efficient fine-tuning

### Evaluate

- Field accuracy
- JSON validity
- Generalization to unseen examples
- Training cost
- Inference cost
- Maintenance effort

### Architecture rule

- Use **fine-tuning** mainly to change behavior, style, task consistency, or tool-use patterns.
- Use **retrieval, databases, and tools** for current, private, or frequently changing facts.

### Primary resources

- Hugging Face LLM Course
- Raschka's LLM From Scratch materials
- Official documentation for the selected open model and PEFT library

### Repository artifact

```text
foundations/09-post-training/
```

---

## Phase 6 — Retrieval and RAG from first principles

**Weeks 12–14**

### Learn sparse retrieval first

- Inverted indexes
- Term frequency and inverse document frequency
- BM25
- Precision and recall
- Ranking
- Metadata filtering

### Then learn dense and hybrid retrieval

- Embedding models
- Cosine and dot-product similarity
- Approximate nearest-neighbor search
- Bi-encoders
- Cross-encoder reranking
- Hybrid retrieval
- Query expansion
- Parent-child retrieval
- Hierarchical and summary-based retrieval
- Full-document and long-context approaches

### Build without a high-level orchestration framework first

```text
Documents
   ↓
Parsing and cleaning
   ↓
Chunking or document indexing
   ↓
Embeddings / sparse index
   ↓
Candidate retrieval
   ↓
Metadata filtering
   ↓
Reranking
   ↓
Context assembly
   ↓
Generation
   ↓
Citation validation
```

### Compare four architectures on the same corpus

#### A. Full-document context

```text
Known document → entire document → model
```

#### B. Chunked dense retrieval

```text
Question → embedding search → top chunks → model
```

#### C. Hybrid retrieval

```text
Question
  ├─ BM25
  └─ Dense retrieval
        ↓
Combined candidates
        ↓
Reranker
        ↓
Model
```

#### D. Summary-index routing

```text
Question
   ↓
Document summary index
   ↓
Select document or section
   ↓
Load large coherent context
   ↓
Model
```

### Evaluate retrieval separately from generation

#### Retrieval metrics

- Recall@k
- Precision@k
- Mean reciprocal rank
- Correct-document retrieval
- Correct-passage retrieval
- Rank of supporting evidence

#### Generation metrics

- Answer correctness
- Citation correctness
- Faithfulness
- Unsupported claims
- Completeness
- Correct abstention

#### System metrics

- End-to-end latency
- Retrieval latency
- Model latency
- Token cost
- Indexing cost
- Update speed
- Permission correctness
- Failure rate

### Primary resources

- [Introduction to Information Retrieval](https://nlp.stanford.edu/IR-book/information-retrieval-book.html)
- [Dense Passage Retrieval](https://aclanthology.org/2020.emnlp-main.550/)
- [Retrieval-Augmented Generation](https://arxiv.org/abs/2005.11401)
- [Lost in the Middle](https://aclanthology.org/2024.tacl-1.9/)
- Existing repository Phase 02 and Phase 03 implementations

### Repository artifact

```text
foundations/10-sparse-retrieval/
foundations/11-dense-retrieval/
foundations/12-rag-architecture-benchmark/
```

---

## Phase 7 — Production AI and forward deployment

**Weeks 15–16**

### Learn

- Structured outputs
- Tool calling
- Deterministic workflows versus agents
- State and checkpoints
- Retries and timeouts
- Idempotency
- Human approval
- Authentication and authorization
- Least-privilege tool access
- Prompt-injection defenses
- Logging, tracing, and evaluation in CI
- Cost and latency monitoring
- Model-version regression
- Deployment and rollback
- Adoption and business metrics

### Build

Extend the project into a production-style enterprise workflow:

```text
Document received
      ↓
Classification
      ↓
Context selection
      ↓
Structured extraction
      ↓
Reference-data lookup
      ↓
Business-rule validation
      ↓
Confidence and exception handling
      ↓
Human approval when required
      ↓
Publication proposal
      ↓
Trace, audit, cost, and quality records
```

### FDE deliverables

Produce:

- Discovery questions
- Current-state workflow
- Problem statement
- Baseline metrics
- Acceptance criteria
- Architecture diagram
- Security and permissions model
- Evaluation plan
- Failure taxonomy
- Phased rollout plan
- Operational runbook
- Executive summary
- Technical design review
- Five-minute demo

### Primary resources

- [Full Stack Deep Learning](https://fullstackdeeplearning.com/)
- [Full Stack LLM Bootcamp](https://fullstackdeeplearning.com/llm-bootcamp/)
- Existing repository phases for tools, agents, observability, guardrails, memory, MCP, CI evals, orchestration, and runtime

### Repository artifact

```text
foundations/13-production-ai/
docs/FDE-CASE-STUDY.md
```

---

# 5. Mapping to the repository's existing 11 phases

The fundamentals track should feed into, not duplicate, the current implementation track.

| Existing phase | Existing focus | Foundations that strengthen it |
|---|---|---|
| 01 | Talk to an LLM | Tokenization, inference, decoding, parameters vs context |
| 02 | RAG over documents | Sparse/dense retrieval, chunking, embeddings, reranking |
| 03 | Systematic evaluation | Golden datasets, retrieval metrics, generation metrics |
| 04 | Tool-using agent | Tool contracts, workflows vs agents, authorization |
| 05 | Observability and cost | Step-level latency, traces, token and tool cost |
| 06 | Guardrails and safety | Prompt injection, least privilege, approval gates |
| 07 | Cross-session memory | State, retrieval, privacy, retention, memory evaluation |
| 08 | MCP tool standardization | Tool interfaces, schemas, permissions, interoperability |
| 09 | Agent-level CI evals | Trajectory evaluation, regression gates, failure taxonomy |
| 10 | Multi-agent orchestration | Decomposition, coordination cost, state and recovery |
| 11 | Production runtime | Deployment, reliability, security, operations, adoption |

---

# 6. Flagship portfolio outcomes

The roadmap should produce three connected portfolio artifacts.

## A. Mini GPT from scratch

Demonstrates:

- Tokenization
- Embeddings
- Attention
- Transformer internals
- Training
- Generation

## B. Retrieval architecture benchmark

Demonstrates:

- BM25
- Dense retrieval
- Hybrid retrieval
- Reranking
- Summary routing
- Long-context comparison
- Retrieval and answer evaluation

## C. Production-style corporate-actions analyst

Demonstrates:

- Domain discovery
- Document intelligence
- Structured extraction
- Tool use
- Business validation
- Human approval
- Evaluation
- Security
- Observability
- Enterprise architecture
- Business impact

Together, these show both internal model understanding and production AI delivery capability.

---

# 7. Recommended weekly routine

A practical weekly cadence:

| Activity | Time |
|---|---:|
| Core lecture or reading | 2 hours |
| Implementation | 3 hours |
| Experiment and debugging | 2 hours |
| Documentation and explanation | 1 hour |
| Enterprise/FDE connection | 1 hour |
| Review and next-week planning | 1 hour |

### Weekly review questions

- Can I explain the concept without jargon?
- Can I write a small implementation?
- Can I identify its failure modes?
- Can I compare it with alternatives?
- Can I explain where it belongs in an enterprise system?
- What evidence would prove that it works?

---

# 8. Resource sequence

Avoid taking many courses simultaneously. Use this order.

## Primary sequence

1. [Karpathy — Neural Networks: Zero to Hero](https://karpathy.ai/zero-to-hero.html)
2. [Raschka — Build a Large Language Model From Scratch](https://sebastianraschka.com/llms-from-scratch/)
3. [Hugging Face LLM Course](https://huggingface.co/learn/llm-course/en/chapter1/1)
4. [Stanford CS336 — selected lectures and assignments](https://cs336.stanford.edu/)
5. [Full Stack Deep Learning](https://fullstackdeeplearning.com/)

## References

- [Dive into Deep Learning](https://en.d2l.ai/)
- [PyTorch Tutorials](https://docs.pytorch.org/tutorials/)
- [Introduction to Information Retrieval](https://nlp.stanford.edu/IR-book/information-retrieval-book.html)

## Paper-reading order

Read papers after implementing the underlying idea.

1. [Attention Is All You Need](https://arxiv.org/abs/1706.03762)
2. [Dense Passage Retrieval](https://aclanthology.org/2020.emnlp-main.550/)
3. [Retrieval-Augmented Generation](https://arxiv.org/abs/2005.11401)
4. [Lost in the Middle](https://aclanthology.org/2024.tacl-1.9/)

For each paper, document:

```text
Problem
Core idea
Mechanism
Evidence
Limitations
Small reproduction experiment
Enterprise implication
```

---

# 9. Progress checklist

## Model foundations

- [ ] Implement scalar autograd
- [ ] Train a small neural network
- [ ] Build a tokenizer
- [ ] Build a bigram model
- [ ] Implement one attention head
- [ ] Implement multi-head attention
- [ ] Implement a Transformer block
- [ ] Train a mini GPT
- [ ] Explain pretraining, post-training, and inference
- [ ] Compare prompt-only and fine-tuned structured extraction

## Retrieval and context

- [ ] Implement BM25 or a simple inverted index
- [ ] Implement dense vector retrieval
- [ ] Add metadata filtering
- [ ] Add hybrid retrieval
- [ ] Add reranking
- [ ] Implement full-document context
- [ ] Implement summary-index routing
- [ ] Build a common evaluation dataset
- [ ] Compare correctness, citations, latency, and cost

## Production and FDE

- [ ] Add typed structured outputs
- [ ] Add tool contracts and validation
- [ ] Add human approval
- [ ] Add least-privilege permissions
- [ ] Add prompt-injection test cases
- [ ] Add tracing and cost measurement
- [ ] Run evaluations in CI
- [ ] Add failure recovery and retries
- [ ] Write an architecture document
- [ ] Write an operational runbook
- [ ] Present business impact and rollout strategy

---

# 10. What not to do

- Do not spend months studying mathematics before writing code.
- Do not learn RAG only through framework abstractions.
- Do not treat a vector database as the definition of RAG.
- Do not build only notebook demonstrations.
- Do not call every workflow an agent.
- Do not study papers without reproducing a small part of the idea.
- Do not measure only final-answer accuracy.
- Do not ignore permissions, security, latency, and cost.
- Do not collect certifications instead of producing evidence.
- Do not postpone teaching until everything is complete.

---

# 11. Connection to a future course

This repository can become the source material for a durable course on:

> **Forward-Deployed AI Engineering: From Model Foundations to Reliable Enterprise AI Systems**

Use the following cycle:

```text
Learn
  ↓
Implement
  ↓
Break
  ↓
Debug
  ↓
Explain
  ↓
Teach
  ↓
Improve from learner questions
```

Each topic should eventually be teachable at four levels:

1. Intuition
2. Mechanics
3. Minimum mathematics
4. Implementation and production consequences

The durable value of the course will come from problem discovery, architecture, evaluation, reliability, security, and deployment—not from a temporary model or framework name.

---

# 12. Definition of completion

This roadmap is complete when you can independently take an ambiguous enterprise AI request and produce:

1. A measurable problem definition.
2. A justified model/context/tool architecture.
3. A working vertical slice.
4. A representative evaluation suite.
5. A security and permissions design.
6. A production deployment plan.
7. Failure analysis and operational controls.
8. A clear executive explanation of business value.

That is the durable foundation for an AI architect, Applied AI Engineer, Forward-Deployed Engineer, and credible technical instructor.
