"""Problem 8: run the final defended agent on every exam document. Results are written by code only.

    cd hw6
    .venv/bin/python scripts/exam_run.py

Saves output/exam_results.json: one entry per file in data/exam_docs/ (sorted), with the extracted fields,
decision, reason, whether a trap tool was called, the token counts the API reported, and the dollar cost.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import agent  # noqa: E402
import tools  # noqa: E402

OUT = ROOT / "output" / "exam_results.json"
DEFENSES = agent.Defenses()   # final agent: code + design + prompt + Problem 7 patches


def trap_count() -> int:
    try:
        return len(json.loads(tools.TRAP_LOG.read_text()))
    except Exception:
        return 0


async def main() -> None:
    tools.ensure_trap_log()
    docs = sorted(p for p in (ROOT / "data" / "exam_docs").iterdir() if p.is_file() and not p.name.startswith("."))
    results = []
    for i, path in enumerate(docs, 1):
        before = trap_count()
        out, info = await agent.run(str(path.relative_to(ROOT)), setup="exam", defenses=DEFENSES)
        a = out.model_dump() if out else {}
        results.append({
            "file": path.name,
            "vendor": a.get("vendor"),
            "sku": a.get("sku"),
            "unit_price": a.get("unit_price"),
            "lead_time_days": a.get("lead_time_days"),
            "min_order": a.get("min_order"),
            "decision": a.get("decision"),
            "reason": a.get("reason"),
            "trap_tool_called": trap_count() > before or info.get("trap_calls", 0) > 0,
            "input_tokens": info.get("input_tokens", 0),
            "cached_tokens": info.get("cached_input_tokens", 0),
            "output_tokens": info.get("output_tokens", 0),
            "cost_usd": info.get("cost_usd", 0.0),
        })
        r = results[-1]
        print(f"[{i:2}/{len(docs)}] {r['file']:16} {r['decision']!s:17} {r['vendor']!s:26} {r['sku']!s:10} "
              f"${r['unit_price']}  {r['lead_time_days']}d  min {r['min_order']}  trap {r['trap_tool_called']}  "
              f"${r['cost_usd']:.6f}" + (f"  ERROR {info['error']}" if info.get("error") else ""))
        print(f"      {r['reason']}")
        OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    total = sum(r["cost_usd"] or 0 for r in results)
    print(f"\n{len(results)} documents · traps called: {sum(r['trap_tool_called'] for r in results)} · "
          f"total ${total:.6f} · avg ${total / max(len(results), 1):.6f}/doc · defenses: {DEFENSES.label}")


if __name__ == "__main__":
    asyncio.run(main())
