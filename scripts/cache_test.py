"""Problem 4: run all 12 practice documents with and without prompt caching.

    cd hw6
    .venv/bin/python scripts/cache_test.py              # both setups, 12 docs each (24 runs, ~48 model calls)
    .venv/bin/python scripts/cache_test.py --only without_cache

Every model call (not just every run) is saved to output/cache_test.json with the setup, document,
every token count the API reported, and the dollar cost from data/prices.json.

Setups
  with_cache     static prompt (instructions + handbook) as the prefix, implicit caching on,
                 one prompt_cache_key for every call so they land on the same cache.
  without_cache  OpenAI prompt_cache_options mode="explicit" with no breakpoints (= create and read no cache)
                 PLUS a random line at the top of every request, so even if the setting were ignored
                 no two requests would share a prefix.
The script then checks the API's numbers: a without_cache call that reports ANY cached tokens fails the check.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import agent  # noqa: E402

OUT = ROOT / "output" / "cache_test.json"
DOCS = sorted((ROOT / "data" / "practice_docs").iterdir())
SETUPS = {
    "with_cache": dict(cache=True, nonce=False),
    "without_cache": dict(cache=False, nonce=True),
}


def load() -> dict:
    if OUT.exists():
        return json.loads(OUT.read_text())
    return {"model": agent.MODEL_NAME, "prices_per_1m": agent.PRICES[agent.MODEL_NAME],
            "setups": {
                "with_cache": "Static prefix (prompt.md + handbook), OpenAI implicit prompt caching, "
                              f"prompt_cache_key={agent.CACHE_KEY!r}.",
                "without_cache": "prompt_cache_options mode='explicit' with no cache breakpoints (no cache "
                                 "created or read) + a random request id as the first line of every request."},
            "calls": [], "runs": []}


async def run_setup(name: str, data: dict) -> None:
    opts = SETUPS[name]
    print(f"\n=== {name} ===")
    for i, path in enumerate(DOCS, 1):
        doc = str(path.relative_to(ROOT))
        out, info = await agent.run(doc, setup=name, defenses=agent.NO_DEFENSES, **opts)
        ok = agent.key_fields_ok(doc, out)
        score = f"{sum(ok.values())}/6" if ok else "n/a"
        for c in info["calls"]:
            data["calls"].append({"setup": name, "document": path.name, "run_id": info["run_id"],
                                  "time": agent.tools.now(), **c})
        data["runs"].append({"setup": name, "document": path.name, "run_id": info["run_id"],
                             "seconds": info["seconds"], "model_calls": len(info["calls"]),
                             "input_tokens": info.get("input_tokens"),
                             "cached_input_tokens": info.get("cached_input_tokens"),
                             "cache_write_tokens": info.get("cache_write_tokens"),
                             "output_tokens": info.get("output_tokens"),
                             "cost_usd": info.get("cost_usd"), "key_match": score,
                             "decision": out.decision if out else None, "error": info["error"]})
        OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False))   # save after every doc
        print(f"[{i:2}/12] {path.name:32} calls {len(info['calls'])}  in {info.get('input_tokens', 0):>6,}  "
              f"cached {info.get('cached_input_tokens', 0):>6,}  write {info.get('cache_write_tokens', 0):>6,}  "
              f"out {info.get('output_tokens', 0):>4}  ${info.get('cost_usd', 0):.6f}  key {score}"
              + (f"  ERROR {info['error']}" if info["error"] else ""))


def summarize(data: dict) -> dict:
    s = {}
    for name in SETUPS:
        calls = [c for c in data["calls"] if c["setup"] == name]
        runs = [r for r in data["runs"] if r["setup"] == name]
        if not calls:
            continue
        tot = lambda k: sum(c.get(k) or 0 for c in calls)
        s[name] = {"documents": len(runs), "model_calls": len(calls),
                   "input_tokens": tot("input_tokens"), "cached_input_tokens": tot("cached_input_tokens"),
                   "cache_write_tokens": tot("cache_write_tokens"),
                   "uncached_input_tokens": tot("uncached_input_tokens"), "output_tokens": tot("output_tokens"),
                   "total_cost_usd": round(tot("cost_usd"), 8),
                   "cost_per_document_usd": round(tot("cost_usd") / max(len(runs), 1), 8),
                   "calls_with_cache_read": sum(1 for c in calls if c.get("cached_input_tokens")),
                   "calls_with_cache_write": sum(1 for c in calls if c.get("cache_write_tokens")),
                   "key_6_of_6": sum(1 for r in runs if r["key_match"] == "6/6"),
                   "errors": sum(1 for r in runs if r["error"])}
    w, n = s.get("with_cache"), s.get("without_cache")
    if w and n:
        s["percent_saved_with_cache"] = round(100 * (1 - w["total_cost_usd"] / n["total_cost_usd"]), 2)
    if n:
        s["without_cache_check"] = ("PASS: no call reported cached or cache-write tokens"
                                    if n["calls_with_cache_read"] == 0 and n["calls_with_cache_write"] == 0
                                    else f"FAIL: {n['calls_with_cache_read']} call(s) read cache, "
                                         f"{n['calls_with_cache_write']} wrote cache")
    if w:
        s["with_cache_check"] = f"{w['calls_with_cache_read']}/{w['model_calls']} calls read from cache"
    return s


async def main(only: str | None, fresh: bool) -> None:
    if fresh and OUT.exists():
        OUT.rename(OUT.with_name(f"cache_test.old-{int(time.time())}.json"))
    data = load()
    for name in SETUPS:
        if only in (None, name):
            await run_setup(name, data)
    data["summary"] = summarize(data)
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print("\n" + json.dumps(data["summary"], indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=list(SETUPS))
    ap.add_argument("--keep", action="store_true", help="append to the existing cache_test.json instead of starting fresh")
    a = ap.parse_args()
    asyncio.run(main(a.only, fresh=not a.keep))
