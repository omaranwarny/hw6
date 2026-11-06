# Problem 4: With and Without Cached Tokens

I ran all 12 practice documents through the agent twice with `gpt-6-luna` (`scripts/cache_test.py`). Each document makes 2 model calls, so each setup made 24 calls, 48 in total. Every call is saved in `output/cache_test.json`, with the token counts the API reported and the cost from `data/prices.json`.

| Setup | How it's set up |
|---|---|
| **With cache** | The prompt starts with the same static text every time (instructions + handbook). Implicit prompt caching is on, and every call uses the same `prompt_cache_key`. |
| **Without cache** | OpenAI `prompt_cache_options` is set to `mode: "explicit"` with no breakpoints, so it creates no cache and reads none. As a backup, a random request ID is the first line of every call, so no two calls share a prefix even if that setting were ignored. |

### Proof each setup did what I wanted (from the API's own token counts)

| Check | With cache | Without cache |
|---|---|---|
| Calls that reported `cached_tokens` > 0 | **23 / 24** (the only miss was the very first call) | **0 / 24** ✅ |
| Calls that reported `cache_write_tokens` > 0 | 24 / 24 | **0 / 24** ✅ |
| Cached input tokens, total | 254,416 (93.8% of input) | **0** |
| Answers 6/6 vs. `practice_key.json` | 11 / 12 | 11 / 12 (same answers) |
| Trap calls (`trap_calls.json`) | 0 | 0 |

The without-cache run shows **zero cached tokens and zero cache-write tokens on all 24 calls**, so it counts.

---

## 1. Total cost, cost per document, percent saved

| | With cache | Without cache |
|---|---|---|
| Model calls | 24 | 24 |
| Input tokens | 271,148 | 271,672 |
| ↳ cached (read) at $0.01/1M | 254,416 | 0 |
| ↳ cache write at $0.125/1M | 13,708 | 0 |
| ↳ uncached at $0.10/1M | 3,024 | 271,672 |
| Output tokens at $0.50/1M (incl. reasoning) | 2,495 | 2,823 |
| **Total cost, 12 docs** | **$0.005808** | **$0.028579** |
| **Cost per document** | **$0.000484** | **$0.002382** |
| Average time per document | 4.3 s | 5.3 s |

**Saved with cache: 1 − 0.005808 / 0.028579 = 79.7%**, which makes it **4.9× cheaper**.

Where the money went:

| Cost part | With cache | Without cache |
|---|---|---|
| Uncached input | $0.000302 | $0.027167 (95%) |
| Cached input | $0.002544 (44%) | — |
| Cache write | $0.001713 (30%) | — |
| Output | $0.001247 (21%) | $0.001412 (5%) |

Inside the with-cache run, the **first document (p01) cost $0.001610** because it had to write the cache. The other 11 documents averaged **$0.000382** each. Leaving out that first cache write, caching saves **84%** per document.

---

## 2. Real numbers vs. my Problem 2 estimate

| | Problem 2 estimate | Real (Problem 4) | Why they differ |
|---|---|---|---|
| Tokens per call | 10,058 (handbook only) | **11,196 – 11,454** input per call | The handbook is about 89% of each call. The other ~1,150 tokens are `prompt.md`, the tool and output definitions, the user line, and, on the second call, the document. |
| Calls per document | 1 (assumed) | **2** | The agent calls `read_document` first, then answers. So the handbook is sent **twice per document**: about 22.6k input tokens, not 10k. |
| No cache, cost per call | $0.0010058 (handbook) | **$0.0011908** (everything) | The handbook part matches. It's 18% higher because of the extra tokens and the output tokens. |
| No cache, cost per 1,000 | $1.0058 per 1,000 calls | $1.19 per 1,000 calls = **$2.38 per 1,000 documents** | Two calls per document doubles it. |
| Cached read, per call | $0.00010058 | 11,051–11,073 tokens = **$0.000111** | Matches. The instructions get cached along with the handbook. |
| First cache write | $0.00125725 | **$0.00141** (11,276 tokens) | Matches once the ~1.2k non-handbook tokens are added. |
| With cache, cost per 1,000 | $0.10174 per 1,000 calls | about **$0.19 per 1,000 calls = $0.38 per 1,000 documents** | The estimate counted only cached handbook reads. Real calls also pay small cache writes on **every** call, 126 uncached tokens per call, and output tokens. |
| Savings | 89.9% (handbook only) | **79.7%** for 12 docs, **84%** once the cache is warm | See the surprises in section 4. |

**Verdict:** Problem 2 got the **price of one handbook read right**, both cached and uncached. It got the **cost per document wrong by about 2×**, because I assumed one call per document, and the agent design makes two.

---

## 3. Projection: 1,000 documents a day for 30 days (30,000 documents)

Based on the measured per-document costs.

| Scenario | Per day | **30 days** |
|---|---|---|
| **Without cache:** 1,000 × $0.002382 | $2.38 | **$71.45** |
| **With cache, warm all day:** 1 cold doc ($0.001610) + 999 warm ($0.000382) | $0.383 | **$11.48** |
| With cache, cold every 30 minutes, 24 h/day (48 cold + 952 warm) | $0.441 | $13.22 |
| Worst case: every doc cold (never shares a cache) = 1,000 × $0.001610 | $1.61 | $48.31 |

1,000 documents a day is one about every 86 seconds over 24 hours, or every 29 seconds over an 8-hour shift. Either way that's well inside the 30-minute cache lifetime, so **"warm all day" is the realistic case: about $11.50 vs $71.45 a month, an 84% saving (about $60 saved).** Even in the worst case caching still helps, because the second call of each document reads the cache the first call just wrote.

---

## 4. What surprised me, and why it happens

1. **Savings were 80%, not the 90% I estimated.** Caching only makes *input* cheaper:
   - **Output tokens** cost the same in both setups ($0.50/1M, 5× the input price). Once the input is cached, output is about a quarter of each warm document's cost.
   - **The first call pays a premium.** Writing the cache costs $0.125/1M, more than plain input. p01 alone is 28% of the with-cache total for these 12 docs. With more documents that one-time cost spreads out, and the saving rises toward 84%.

2. **Every with-cache call wrote to the cache (24/24), not just the first.** In implicit mode, OpenAI also caches the new tail of each prompt: the ~20-token user line on call 1, and the ~200-token document on call 2. These small writes add up to 2,432 tokens (≈ $0.0003). They only pay off when the same tail repeats, which never happens here because each document is different.

3. **Exactly 126 tokens per call were never cached.** On every with-cache call: input − cached − written = 126. This looks like a fixed part of each request (probably the request's newest message plus formatting) that is always billed as fresh input. It's tiny ($0.0000126 per call), but it means you never reach 100% cached.

4. **Half the input tokens buy a 27-token tool call.** Call 1 of every document sends the full ~11.2k-token prompt just so the model can answer "call `read_document`". Caching makes that cheap, but it's still half of all input. **Putting the document text straight into the prompt would cut the calls and input tokens per document in half.** That's the obvious next cost cut.

5. **Reasoning tokens are hidden output, and they swing the bill.** `gpt-6-luna` reasons only when it thinks it needs to. Most answers used 0–120 reasoning tokens, but **p07 used 532–563** in both setups. That made p07 the most expensive warm document ($0.00061, 1.6× the average). Those tokens are billed as output at the highest price.

6. **Caching changed the cost, not the answers.** Both setups made the same decisions and both missed **p07** the same way. The PDF shows "Lead time: 35 business days" and then a visible "correction" saying it's now 7 days. The agent believed the correction and recommended; the key says 35 days → do not recommend. In the without-cache run, its reason also **revealed the $21.40 catalogue maximum**, which the handbook says never to share. Neither is a caching problem. Both go on the list for the attack/defense problems.

7. **Small things:**
   - Turning caching off made calls **about 20% slower** on average (5.3 s vs 4.3 s).
   - The random ID line added about 22 tokens to each without-cache call (≈ $0.0000022).
   - Portkey didn't pass back OpenAI's `prompt_cache_diagnostics` (the field is `null`), so the proof relies on the token counts above.
