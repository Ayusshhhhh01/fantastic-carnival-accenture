"""
CAUSE LLM layer — Steps 8 & 9 ONLY.

The LLM's entire job in this system:
  Step 8  narrate(payload, persona): finished JSON -> natural language.
  Step 9  self_verify(text, payload): find claims not supported by the JSON.

If no API key is configured the module runs in OFFLINE TEMPLATE MODE: text is
assembled by deterministic code from exactly the same JSON (clearly labelled
in the UI), so the demo never depends on network access and the hard rule
(LLM never computes numbers) still holds either way.
"""
import json
import os
import re
import time

import requests

from .engine import fmt_inr

MODEL = os.environ.get("CAUSE_LLM_MODEL", "gpt-4o-mini")
BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
COST_PER_1K = 0.0006  # rough blended estimate for the ledger


def llm_available() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def _chat(system: str, user: str):
    t0 = time.perf_counter()
    resp = requests.post(
        f"{BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
        json={"model": MODEL,
              "messages": [{"role": "system", "content": system},
                           {"role": "user", "content": user}],
              "temperature": 0.0},
        timeout=60)
    resp.raise_for_status()
    data = resp.json()
    latency = time.perf_counter() - t0
    tokens = data.get("usage", {}).get("total_tokens", 800)
    return data["choices"][0]["message"]["content"], latency, \
        tokens / 1000 * COST_PER_1K


NARRATE_SYSTEM = (
    "You are a retail analytics narrator. Use only the facts and numbers "
    "provided in the JSON. Never add, infer, or estimate anything not "
    "present in this JSON. Do not compute new numbers; reuse the provided "
    "ones verbatim. Keep the note UNDER 110 WORDS. Be direct and factual - "
    "no greetings, no filler, no hedging."
)


def _persona_instructions(persona: str) -> str:
    if persona == "CXO":
        return ("Audience: CXO. Lead with the headline number and whether "
                "the cause is resolved or unresolved. Give ONE strategic "
                "action. Do NOT mention SKU/product-level details - only "
                "category aggregates appear in your copy.")
    return ("Audience: Category Manager. Be operational: name the specific "
            "product(s), regions, dates and computed numbers from the JSON, "
            "and give a tactical next action grounded in the recommendation "
            "field.")


# ------------------------------------------------------- offline fallback --
def _offline_narrate(payload: dict, persona: str) -> str:
    """Short analyst note assembled strictly from payload numbers."""
    a = payload["alert"]
    rec = payload["recommendation"]

    if payload["route"] == "ABSTAIN":
        return (f"{a['kpi']} for {a['category']} / {a['region']} moved "
                f"{a['delta_fmt']} in the week of {a['week_start']}. "
                f"{payload['abstention']['message']}")

    if payload["route"] == "FAST_PATH":
        fp = payload["fast_path"]
        return (f"{a['kpi']} for {a['category']} / {a['region']} came in at "
                f"{a['current_fmt']} vs a {a['baseline_fmt']} baseline "
                f"({a['pct_fmt']}, impact {a['delta_fmt']}). A logged event "
                f"explains it directly: [{fp['event_type']}] on "
                f"{fp['event_date']} - {fp['description']}. Confidence 95%. "
                f"Action: {rec['action']}")

    winner = next((h for h in payload["hypotheses"] if h["supported"]),
                  payload["hypotheses"][0])
    rejected = [h for h in payload["hypotheses"] if h is not winner]
    d = winner.get("detail", {})

    lines = []
    if persona == "CXO":
        status = ("unresolved - flagged for review"
                  if payload["route"] == "UNRESOLVED_CONFLICT"
                  else f"explained at {winner.get('confidence_pct', 90)}% "
                       f"confidence")
        lines.append(f"{a['category']} {a['kpi'].lower()} in {a['region']} "
                     f"is {a['pct_fmt']} vs baseline ({a['delta_fmt']}).")
        lines.append(f"Cause: {winner['name'].lower()}, {status}.")
        if payload["route"] == "UNRESOLVED_CONFLICT":
            lines.append("Evidence conflicts across comparable regions - "
                         "manual review advised.")
        lines.append(f"Strategic action: {rec['action']}")
        return " ".join(lines)

    # Category Manager
    lines.append(f"{a['kpi']} for {a['category']} / {a['region']} is "
                 f"{a['pct_fmt']} vs the trailing 4-week baseline "
                 f"({a['delta_fmt']}).")
    if winner["name"].startswith("Supply") and d:
        lines.append(f"Cause: stock-out of {d.get('product_name')} - "
                     f"expected {d.get('counterfactual_fmt')} over the "
                     f"outage window vs {d.get('actual_fmt')} actual, i.e. "
                     f"{d.get('explains_pct')}% of the move.")
    else:
        lines.append(f"Cause: {winner['name'].lower()} - "
                     f"{winner['deciding_value']}")
    for h in rejected[:2]:
        lines.append(f"Ruled out: {h['name'].lower()} "
                     f"({h['deciding_value'].split(';')[0]}).")
    if payload["route"] == "UNRESOLVED_CONFLICT":
        lines.append(f"Conflict: {payload['conflict']['signal_b']}")
    lines.append(f"Confidence {winner.get('confidence_pct', 90)}%. "
                 f"Action: {rec['action']}"
                 + (f" Est. recovery {rec['est_impact_fmt']}/wk."
                    if rec.get("est_impact_fmt") else ""))
    return " ".join(lines)


# ------------------------------------------------------------- Step 8 -----
def narrate(payload: dict, persona: str, ledger_add=None):
    """Returns (text, engine_label)."""
    if llm_available():
        try:
            sys_p = NARRATE_SYSTEM + " " + _persona_instructions(persona)
            out, latency, cost = _chat(sys_p,
                                       json.dumps(payload, default=str))
            if ledger_add:
                ledger_add("Step 8 Narrate (" + persona + ")",
                           "LLM call", time.perf_counter() - latency,
                           f"persona={persona}", cost)
            return out.strip(), f"LLM ({MODEL})"
        except Exception as e:  # fall back rather than break the demo
            txt = _offline_narrate(payload, persona)
            return txt, f"OFFLINE template (LLM error: {type(e).__name__})"
    txt = _offline_narrate(payload, persona)
    return txt, "OFFLINE template mode (no API key configured)"


# ------------------------------------------------------------- Step 9 -----
NUM_TOKEN = re.compile(r"(₹\s?[\d,]+(?:\.\d+)?\s?(?:Cr|L|cr|l)?|\d+(?:\.\d+)?%)")


def _is_num(x):
    try:
        float(x)
        return True
    except ValueError:
        return False


def _allowed_numbers(payload: dict):
    allowed = set()

    def walk(o):
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, bool) or o is None:
            pass
        elif isinstance(o, (int, float)):
            x = float(o)
            for v in (x, abs(x)):
                allowed.add(f"{v:,.0f}")
                allowed.add(f"{v:.1f}")
                allowed.add(f"{v:.2f}")
                allowed.add(str(int(v)))
                allowed.add(fmt_inr(v))
                allowed.add(fmt_inr(-v))
                allowed.add(f"{v/1e5:.1f}L")
                allowed.add(f"{v/1e7:.2f}Cr")
        elif isinstance(o, str):
            allowed.add(o)
            for tok in NUM_TOKEN.findall(o):
                allowed.add(tok.replace(" ", ""))

    walk(payload)
    return allowed


def self_verify(text: str, payload: dict, ledger_add=None):
    """Return (clean_text, removed_claims list)."""
    removed = []
    engine = ""
    if llm_available():
        try:
            sys_p = ("You are a fact auditor. Given a narrative and the JSON "
                     "it was generated from, list every factual claim or "
                     "number in the narrative that is NOT directly supported "
                     "by a field in the JSON. Return a strict JSON array of "
                     "the unsupported claim strings; return [] if none.")
            raw, latency, cost = _chat(sys_p,
                                       "JSON:\n" +
                                       json.dumps(payload, default=str) +
                                       "\n\nNARRATIVE:\n" + text)
            if ledger_add:
                ledger_add("Step 9 Self-Verify",
                           "LLM call", time.perf_counter() - latency,
                           "claim audit", cost)
            claims = json.loads(raw)
            engine = f"LLM ({MODEL})"
        except Exception:
            claims, engine = None, ""
    else:
        claims, engine = None, ""

    if claims is None:
        # Deterministic numeric-claim audit: every number in the narrative
        # must exist inside the source JSON (any formatting, % aware).
        allowed_raw = _allowed_numbers(payload)
        allowed = {a.replace(" ", "").replace(",", "").rstrip("%").lower()
                   for a in allowed_raw}
        sentences = re.split(r"(?<=[.!?])\s+", text.replace("i.e.", "ie"))
        keep = []
        for s in sentences:
            s = s.replace("ie ", "i.e. ") if s.startswith("ie ") else s
            bad = []
            for tok in NUM_TOKEN.findall(s):
                norm = tok.replace(" ", "").replace(",", "").lower()
                bare = norm.rstrip("%")
                if norm in allowed or bare in allowed:
                    continue
                # tolerate rounding: 19.4% vs 19.42 stored as 0.194 -> check
                try:
                    val = float(bare.rstrip("%"))
                    if any(abs(val - float(a)) <= 0.051
                           for a in [x for x in allowed
                                     if _is_num(x)]):
                        continue
                    # percent values may be stored as fractions (0.194)
                    frac = val / 100
                    if any(abs(frac - float(a)) <= 0.0011
                           for a in [x for x in allowed if _is_num(x)]):
                        continue
                except ValueError:
                    pass
                bad.append(tok)
            if bad:
                removed.append({"claim_sentence": s,
                                "unverified_tokens": bad})
            else:
                keep.append(s)
        clean = " ".join(keep)
        engine = engine or "Deterministic numeric audit (offline mode)"
        return clean, removed, engine

    # LLM path: strip sentences containing any reported claim
    clean = text
    for c in claims:
        s = str(c)
        idx = clean.find(s[:40]) if len(s) > 40 else -1
        removed.append({"claim": s})
    # sentence-level removal
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", clean)]
    keep = []
    for s in sentences:
        if any(str(c)[:30].lower() in s.lower() for c in claims):
            removed.append({"claim_sentence": s})
        else:
            keep.append(s)
    return " ".join(keep), removed, engine
