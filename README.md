# Campus Customs Vendor Desk (HW6: Tokenomics + Prompt Injection)

A **PydanticAI** agent reads one vendor document (HTML quote, PDF, or `.eml` email) for Campus Customs. It pulls out the vendor, SKU, unit price, lead time and minimum order, then applies the Shop Handbook's four purchasing rules to return **recommend** or **do_not_recommend** with a one-sentence reason.

The homework measures what the ~10k-token handbook costs per call, cuts that cost with prompt caching, and defends the agent against booby-trapped vendor documents.

- Every AI call uses **only `gpt-6-luna`** through Portkey. The model is fixed in code.
- `send_email` and `approve_payment` are **trap tools**. They never send or pay anything; they only append to `output/trap_calls.json`.

The results page is **`output/hw6_report.html`**. Double-click it; it works offline.

## Setup

You need Python 3.11+ and a Portkey API key with access to `gpt-6-luna`.

```bash
cd hw6
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                 # then put your key in .env:  PORTKEY_API_KEY=...
```

## Run the agent on one document

```bash
python agent.py --doc data/practice_docs/p01_bluehen_quote.html            # final defended agent (default)
python agent.py --doc data/practice_docs/p07_longwharf_quote.pdf --check   # also compare with practice_key.json
python agent.py --doc data/exam_docs/e09_email.eml
```

`--defenses` picks which defenses are on:

| Flag | Agent |
|---|---|
| `--defenses all` (default) | Code + design + prompt layers, plus the Problem 7 red-team patches |
| `--defenses p6` | The three layers exactly as measured in Problem 6 |
| `--defenses none` | The Problem 3 agent, no defenses (used for the attack and red-team baselines) |
| `--defenses code,prompt` | Any mix of `code`, `design`, `prompt`, `hardened` |

`--no-cache` turns prompt caching off (Problem 4).

Every run prints the answer and a `[usage]` line with the tokens and dollar cost. It also appends to:

- `output/usage_log.json`: tokens and dollars
- `output/audit_trail.json`: tool calls and the final answer
- `output/trap_calls.json`: only if a trap tool was ever called (it's `[]`)

## Reproduce each problem

| Problem | Command | Writes |
|---|---|---|
| 2 Handbook size | `python scripts/count_tokens.py` | `output/handbook_tokens.json` → `handbook_estimate.md` |
| 4 Cache test | `python scripts/cache_test.py` | `output/cache_test.json` → `cache_test.md` |
| 5 Attacks (no defenses) | `python scripts/attack_test.py` | `output/attack_results.json` → `attack_results.md` |
| 6 Defenses | `python scripts/defense_test.py` | `output/defense_results.json`, `defense_ablation.json` → `defense_results.md` |
| 7 Red team | `python scripts/red_team.py` | `output/red_team.json` → `red_team.md` (attacks in `data/my_attacks/`, truth in `attack_key.json`) |
| 8 Exam | `python scripts/exam_run.py` | `output/exam_results.json` (never hand-edited) |
| 9 Report | `python scripts/build_report.py` | `output/hw6_report.html` (built from the JSON results) |

## Files

| Path | What it is |
|---|---|
| `agent.py` | The agent, the defense switches, the cache settings, and usage/audit logging |
| `tools.py` | `read_document` (visible-text reader for HTML/PDF/email, plus the code-layer defenses) and the trap tools |
| `guard.py` | Design layer: handbook rules in code, fact grounding, decision + reason, output scan |
| `models.py` | `VendorDecision`, the structured answer |
| `prompts/prompt.md` | Defended instructions (the handbook is appended at run time) |
| `prompts/prompt_p3.md` | The original Problem 3 prompt, for `--defenses none` |
| `data/` | Course data (handbook, prices, practice docs + key, exam docs) and `my_attacks/` |
| `output/` | All results; `harness.md` describes the fields, tools and safety layers |
| `AI_prompts.md` | My prompts to the vibe coder, one section per problem |

## Safety in one paragraph

Our code reads each document and keeps only what a person would see. It drops hidden HTML, CSS, email and PDF text and flags suspicious lines. The model sees the document only as quoted data, and the email and payment tools are hidden from it and need a human sign-off. The model only *proposes* the five facts. Code checks they appear on the page, applies the handbook's rules, and writes the reason, so it can't leak max unit costs or links. Details are in `output/harness.md` (Safety section).
