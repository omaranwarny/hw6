"""Count how many tokens the Shop Handbook is (Problem 2).

    python scripts/count_tokens.py

Uses tiktoken's o200k_base encoding (OpenAI's current tokenizer,
the one gpt-6-luna's family uses). Writes output/handbook_tokens.json. Problem 4 checks this against
the real usage numbers Portkey returns.
"""
import json
from pathlib import Path

import tiktoken

ROOT = Path(__file__).resolve().parent.parent
text = (ROOT / "data" / "shop_handbook.md").read_text(encoding="utf-8")

o200k = len(tiktoken.get_encoding("o200k_base").encode(text))
cl100k = len(tiktoken.get_encoding("cl100k_base").encode(text))
out = {
    "file": "data/shop_handbook.md",
    "chars": len(text),
    "words": len(text.split()),
    "tokens_o200k_base": o200k,
    "tokens_cl100k_base_for_comparison": cl100k,
    "chars_per_token": round(len(text) / o200k, 2),
}
(ROOT / "output").mkdir(exist_ok=True)
(ROOT / "output" / "handbook_tokens.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
