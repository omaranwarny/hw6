# Handbook Size and Cost Estimate (Problem 2)

## 1. How many tokens is the handbook?

**10,058 tokens.**

**How I got it:** I tokenized `data/shop_handbook.md` with OpenAI's **tiktoken**, using the **`o200k_base`** encoding. That's OpenAI's current tokenizer, the one `gpt-6-luna`'s model family uses. The script is `scripts/count_tokens.py`, and its output is in `output/handbook_tokens.json`:

| Measure | Value |
|---|---|
| Characters | 28,903 |
| Words | 6,127 |
| **Tokens (`o200k_base`)** | **10,058** |
| Tokens (`cl100k_base`, OpenAI's older tokenizer, for comparison) | 10,184 |
| Characters per token | 2.87 |

**Sanity check:** the usual rule of thumb (characters ÷ 4) gives only about 7,226 tokens, which is **28% too low**. This handbook is dense with markdown tables, SKUs (`CC-HD-006`), prices, and numbers, which tokenize into short pieces. That's why it's 2.87 characters per token instead of about 4. The two tokenizers agree within 1.3%.

**Caveat:** this counts the handbook text only. On a real call, the model also sees chat formatting tokens and the rest of the prompt (instructions, the vendor document, tool definitions), so real `input_tokens` will be higher. Problem 4 checks this against real usage.

## 2. What the handbook alone costs

Prices from `data/prices.json` (gpt-6-luna, per 1M tokens):

| | $ per 1M tokens | $ per token |
|---|---|---|
| Input (uncached) | $0.10 | $0.0000001 |
| Cached input (cache read) | $0.01 | $0.00000001 |
| Cache write | $0.125 | $0.000000125 |
| Output | $0.50 | not relevant here: the handbook is input only |

### Without caching (the handbook is billed as normal input every time)

- **One call:** 10,058 tokens × $0.10 ÷ 1,000,000 = **$0.0010058** (about 0.1¢)
- **1,000 calls:** 1,000 × $0.0010058 = **$1.0058** (about $1.01)

### With caching (the handbook is a fixed prefix the provider caches)

- **One call, read from cache:** 10,058 × $0.01 ÷ 1,000,000 = **$0.00010058** (a tenth of the uncached price)
- **One call that writes the cache** (the first call, or after the cache expires): 10,058 × $0.125 ÷ 1,000,000 = **$0.00125725**. That's slightly *more* than uncached.
- **1,000 calls** (1 write + 999 cached reads):
  - $0.00125725 + 999 × $0.00010058
  - = $0.00125725 + $0.10047942
  - = **$0.10174** (about $0.10)

| Handbook cost | 1 call | 1,000 calls |
|---|---|---|
| **No caching** | $0.0010058 | **$1.0058** |
| **With caching** | $0.00010058 (read) / $0.00125725 (first write) | **$0.10174** |
| **Savings** | | **$0.904, about 89.9% less** |

### What this assumes

- **The handbook must be an identical prefix.** Caching only works if the handbook is the **first, unchanged** part of every prompt (system prompt first; the changing vendor document after it). Prompts must also be at least about 1,024 tokens to be cacheable, and the handbook alone is 10× that.
- **The cache expires after a few minutes of inactivity.** Each re-write costs about $0.00126. Even if it had to be rewritten 100 times in 1,000 calls, the total would be about 100 × $0.00126 + 900 × $0.00010 ≈ **$0.216**, still about 79% cheaper than no caching.
- **These numbers are the handbook only.** The vendor document (a few hundred to about 1,000 tokens), our instructions, and the **output tokens at $0.50/1M** (5× the input price) come on top. I'll measure those in Problem 4.
- **The real bill is small but compounds.** About $1 per 1,000 documents sounds small, but the handbook is the biggest single cost driver per call. Problem 3 onward is about cutting it.
