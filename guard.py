"""DESIGN layer (Problem 6): the document can influence the facts the model extracts, never the decision.

- The handbook's rules (approved / removed vendors, max unit costs, 21-day and 600-unit limits) are parsed
  from data/shop_handbook.md once, in code.
- `ground()` keeps a fact only if it literally appears in the visible document text (a number the model
  "heard" from an injection or made up is dropped to null -> that check fails safely).
- `decide()` applies the four checks in code and writes the reason from a template, so the reason can
  never contain a max unit cost, a link, or text copied from the document.
- `scan_output()` is the last gate: no links, email addresses or max unit costs in anything we return.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HANDBOOK = (ROOT / "data" / "shop_handbook.md").read_text(encoding="utf-8")


def _section(num: int) -> str:
    m = re.search(rf"^## {num}\..*?(?=^## \d+\.|\Z)", HANDBOOK, re.M | re.S)
    return m.group(0) if m else ""


def _rows(section: str) -> list[list[str]]:
    rows = []
    for line in section.splitlines():
        if line.startswith("|") and not re.match(r"^\|\s*-", line):
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
    return rows[1:]  # drop header


APPROVED = [r[1] for r in _rows(_section(5))]
REMOVED = [r[0] for r in _rows(_section(6))]
CATALOGUE = {r[0]: {"item": r[1], "max": float(r[4].strip("$").replace(",", ""))}
             for r in _rows(_section(9)) if re.fullmatch(r"CC-[A-Z]{2}-\d{3}", r[0])}
_s4 = _section(4)
MAX_LEAD = int(re.search(r"lead time is (\d+) days or less", _s4).group(1))
MAX_MIN_ORDER = int(re.search(r"minimum order is (\d+) units or less", _s4).group(1))


def _norm(s: str) -> str:
    s = re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())
    s = re.sub(r"\b(inc|llc|ltd|co|company|the)\b", " ", s)
    return " ".join(s.split())


def canonical_vendor(name: str | None) -> tuple[str | None, str]:
    """-> (handbook name, 'approved' | 'removed' | 'unknown')."""
    n = _norm(name or "")
    if not n:
        return None, "unknown"
    for v in REMOVED:
        if _norm(v) and (_norm(v) in n or n in _norm(v)):
            return v, "removed"
    for v in APPROVED:
        if _norm(v) and (_norm(v) in n or n in _norm(v)):
            return v, "approved"
    return name, "unknown"


def _has_number(text: str, value: float, money: bool = False) -> bool:
    t = text.replace(",", "")
    if money:
        forms = {f"{value:.2f}"} | ({f"{int(value)}"} if float(value).is_integer() else set())
        return any(re.search(rf"\$?\s?{re.escape(f)}(?!\d)", t) for f in forms)
    return re.search(rf"(?<![\d.]){int(value)}(?![\d.])", t) is not None


def items_named(text: str) -> list[str]:
    """Catalogue SKUs whose item name appears in the text (longest names first, no overlaps)."""
    t, found = f" {_norm(text)} ", []
    for sku, c in sorted(CATALOGUE.items(), key=lambda kv: -len(kv[1]["item"])):
        name = f" {_norm(c['item'])} "
        if len(name.split()) >= 2 and name in t:
            found.append(sku)
            t = t.replace(name, " ")
    return found


def ground(facts: dict, text: str, hardened: bool = False) -> tuple[dict, list[str]]:
    """Drop any extracted fact that does not appear in the visible document text.
    hardened=True adds the Problem 7 patch: the SKU must belong to the item the document actually names."""
    f, notes = dict(facts), []
    if f.get("unit_price") is not None and not _has_number(text, f["unit_price"], money=True):
        notes.append(f"unit price {f['unit_price']} not found in document"); f["unit_price"] = None
    lt = f.get("lead_time_days")
    if lt is not None and not (_has_number(text, lt) or (lt % 7 == 0 and re.search(
            rf"(?<!\d){lt // 7}\s*(?:-|\s)?weeks?", text, re.I))):
        notes.append(f"lead time {lt} not found in document"); f["lead_time_days"] = None
    if f.get("min_order") is not None and not _has_number(text, f["min_order"]):
        notes.append(f"minimum order {f['min_order']} not found in document"); f["min_order"] = None
    skus_in_doc = sorted(set(re.findall(r"CC-[A-Z]{2}-\d{3}", text)))
    sku = f.get("sku")
    if sku and skus_in_doc and sku not in skus_in_doc:
        notes.append(f"SKU {sku} not in document; using {skus_in_doc[0]}"); f["sku"] = skus_in_doc[0]
    elif sku and sku not in CATALOGUE:
        notes.append(f"SKU {sku} is not in the catalogue"); f["sku"] = None
    elif sku and not skus_in_doc and _norm(CATALOGUE[sku]["item"]) not in _norm(text):
        notes.append(f"SKU {sku} item name not found in document"); f["sku"] = None
    if hardened and f.get("sku") in CATALOGUE:
        named = items_named(text)
        if named and f["sku"] not in named and len(named) == 1:
            notes.append(f"SKU {f['sku']} is the catalogue's '{CATALOGUE[f['sku']]['item']}', but the document names "
                         f"'{CATALOGUE[named[0]]['item']}'; using {named[0]}")
            f["sku"] = named[0]
    if f.get("vendor") and _norm(f["vendor"]) not in _norm(text):
        notes.append(f"vendor '{f['vendor']}' not found in document")
        f["vendor_grounded"] = False
    return f, notes


def decide(f: dict, extra_note: str = "") -> tuple[str, str | None, str]:
    """Handbook section 4, in code. -> (decision, failed_check, one-sentence reason). Never prints a max cost."""
    vendor, status = canonical_vendor(f.get("vendor"))
    sku, price, lead, mo = f.get("sku"), f.get("unit_price"), f.get("lead_time_days"), f.get("min_order")
    if f.get("vendor_grounded") is False or status != "approved":
        why = ("is on the handbook's removed or pending list" if status == "removed"
               else "could not be confirmed from the visible document" if f.get("vendor_grounded") is False
               else "is not on the approved vendor list")
        return "do_not_recommend", "approved_vendor", f"Approved-vendor check fails: {f.get('vendor') or 'the vendor'} {why}{extra_note}."
    if price is None or sku is None or sku not in CATALOGUE:
        what = "the unit price" if price is None else "the Campus Customs SKU"
        return "do_not_recommend", "price", f"Price check fails: {what} is not stated in the document, so it cannot be checked{extra_note}."
    if price > CATALOGUE[sku]["max"]:
        return "do_not_recommend", "price", f"Price check fails: the quoted ${price:.2f} is above our catalogue limit for {sku}{extra_note}."
    if lead is None:
        return "do_not_recommend", "lead_time", f"Lead-time check fails: the document does not state a lead time{extra_note}."
    if lead > MAX_LEAD:
        return "do_not_recommend", "lead_time", f"Lead-time check fails: {lead} days is over the {MAX_LEAD}-day limit{extra_note}."
    if mo is None:
        return "do_not_recommend", "minimum_order", f"Minimum-order check fails: the document does not state a minimum order{extra_note}."
    if mo > MAX_MIN_ORDER:
        return "do_not_recommend", "minimum_order", f"Minimum-order check fails: {mo} units is over the {MAX_MIN_ORDER}-unit limit{extra_note}."
    return "recommend", None, (f"All four checks pass: {vendor} is approved, ${price:.2f} is within our catalogue limit "
                               f"for {sku}, {lead} days is within {MAX_LEAD}, and {mo} units is within {MAX_MIN_ORDER}{extra_note}.")


LINK = re.compile(r"https?://|www\.|\b[\w-]+\.(?:example|com|net|org|io|co)\b(?:/\S*)?", re.I)
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")


def scan_output(text: str, price: float | None = None) -> list[str]:
    """Problems in an answer string: links, email addresses, or any max unit cost (other than the quoted price)."""
    bad = [f"link: {m}" for m in LINK.findall(text)] + [f"email: {m}" for m in EMAIL.findall(text)]
    maxes = {round(c["max"], 2) for c in CATALOGUE.values()}
    for amt in re.findall(r"\$\s?([\d,]+(?:\.\d+)?)", text):
        v = round(float(amt.replace(",", "")), 2)
        if v in maxes and (price is None or abs(v - price) > 0.005):
            bad.append(f"max unit cost ${v:.2f}")
    return bad
