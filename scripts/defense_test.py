"""Problem 6: rerun all 12 practice documents with the defenses on.

    cd hw6
    .venv/bin/python scripts/defense_test.py            # all layers + one run with each layer switched off (48 runs)
    .venv/bin/python scripts/defense_test.py --only all # just the fully defended agent (12 runs)

output/defense_results.json  - fully defended agent, same shape as attack_results.json + tokens and dollars per doc
output/defense_ablation.json - the same 12 docs with each layer switched off in turn (what each layer catches,
                               and the tokens/dollars each layer adds), plus the Problem 5 'before' summary.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import agent  # noqa: E402
import tools  # noqa: E402
from attack_test import DOCS, evaluate, line, summarize  # noqa: E402

D = agent.Defenses
MODES = {   # Problem 6 layers (hardened=False keeps the Problem 6 numbers reproducible)
    "all": D(True, True, True, False),
    "no_code": D(False, True, True, False),      # design + prompt
    "no_design": D(True, False, True, False),    # code + prompt
    "no_prompt": D(True, True, False, False),    # code + design
    "all_p7": D(True, True, True, True),         # + Problem 7 red-team patches (run with --only all_p7)
}
OUT = ROOT / "output" / "defense_results.json"
ABL = ROOT / "output" / "defense_ablation.json"


async def main(only: str | None) -> None:
    tools.ensure_trap_log()
    before = json.loads((ROOT / "output" / "attack_results.json").read_text())
    abl = {"model": agent.MODEL_NAME, "before_problem5": before.get("summary"), "modes": {}}
    for name, d in MODES.items():
        if (only and name != only) or (not only and name == "all_p7"):
            continue
        print(f"\n=== {name} ({d.label}) ===")
        results = []
        for i, path in enumerate(DOCS, 1):
            results.append(await evaluate(path, d, f"defense_{name}"))
            print(line(i, results[-1]))
        summ = summarize(results)
        print(json.dumps(summ, indent=2))
        if name == "all_p7":
            (ROOT / "output" / "defense_results_p7.json").write_text(json.dumps(
                {"model": agent.MODEL_NAME, "agent": "Problem 6 layers + Problem 7 patches", "defenses": d.label,
                 "summary": summ, "documents": results}, indent=2, ensure_ascii=False))
        if name == "all":
            OUT.write_text(json.dumps({"model": agent.MODEL_NAME, "agent": "Problem 6 agent, all three defense layers",
                                       "defenses": d.label, "summary": summ, "documents": results},
                                      indent=2, ensure_ascii=False))
        abl["modes"][name] = {"defenses": d.label, "summary": summ,
                              "per_document": [{k: r[k] for k in ("document", "fooled", "all_fields_match",
                                                                  "trap_tool_called", "strange_text", "model_calls",
                                                                  "tokens", "cost_usd")}
                                               | {"decision": r["decision"]["got"],
                                                  "lead_time": r["fields"]["lead_time_days"]["got"],
                                                  "unit_price": r["fields"]["unit_price"]["got"],
                                                  "guard_notes": r["guard_notes"],
                                                  "model_answer_before_guard": r["model_answer_before_guard"],
                                                  "reason": (r["answer"] or {}).get("reason")}
                                               for r in results]}
        if ABL.exists() and only:
            old = json.loads(ABL.read_text())
            old["modes"].update(abl["modes"])
            abl = old
        ABL.write_text(json.dumps(abl, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=list(MODES))
    asyncio.run(main(ap.parse_args().only))
