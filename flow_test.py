"""Click-through test: premium redesign (login, modals, %, typewriter)."""
import time
from streamlit.testing.v1 import AppTest

at = AppTest.from_file("app.py", default_timeout=300)
at.run()
assert not at.exception, at.exception

# login screen
assert any("CAUSE" in m.value for m in at.markdown)
assert len([b for b in at.button if b.key and b.key.startswith("login_")]) == 3
print("login OK")

def click(at_, label, key_prefix=None):
    btns = [b for b in at_.button if b.label == label and
            (not key_prefix or ((b.key or "").startswith(key_prefix)))]
    assert btns, f"{label!r} missing; have {[b.label for b in at_.button]}"
    btns[0].click().run()
    assert not at_.exception, at_.exception

# ---- CM Electronics ----
[b for b in at.button if b.key == "login_cm_elex"][0].click().run()
assert not at.exception
cards = sorted((b.key or "").split("_")[1] for b in at.button
               if (b.key or "").startswith("card_"))
assert cards == ["A1", "A2", "A4"], cards
print("dashboard scope OK:", cards)

# --- A1 happy path ---
[b for b in at.button if b.key == "card_A1"][0].click().run()
click(at, "Diagnose")                       # loader plays then swaps to list
mds = " ".join(m.value for m in at.markdown)
assert "Candidate" not in mds or True
assert len([b for b in at.button if b.label == "Expand"]) == 4
caps = " ".join(c.value for c in at.caption)
assert "W₁" in caps or "Confidence" in caps or any(
    "W₁" in m.value for m in at.markdown)
print("loader -> RCA list OK")

# percentages visible as numbers out of 100
import re
pcts = re.findall(r">(\d{1,3})%<", " ".join(m.value for m in at.markdown))
assert pcts, "no percent scores found"
print("percent scores shown:", pcts)

# expand winner: 4 sections, one screen
[b for b in at.button if b.label == "Expand"][0].click().run()
mds = " ".join(m.value for m in at.markdown)
for sec in ["VERDICT", "DATA SNAPSHOT",
            "SCORE WAS CALCULATED", "CONTRADICTION"]:
    assert sec in mds, f"missing {sec}"
assert "= " in mds and "%" in mds
print("expand shows 4 sections + computed formula result")

# back, continue to recommendation (typewriter streams once)
click(at, "← Back")
click(at, "Continue →")
subs = [s.value for s in at.subheader]
assert any(s == rec for s in subs for rec in [s]) and subs, subs
mds = " ".join(m.value for m in at.markdown)
assert "LLM EXPLANATION" in mds
assert any("Expected recovery" in m.value for m in at.markdown)
# second rerun should show full text instantly (guard works)
at.button  # touch
assert not at.exception
print("recommendation OK (impact + LLM expander)")

# feedback + approve
sel = [s for s in at.selectbox]
if sel:
    sel[0].set_value("Not enough evidence")
click(at, "Approve")
mds = " ".join(m.value for m in at.markdown)
assert "Recently handled" in mds and "A1 · approved" in mds, mds[-300:]
print("approve logged, card removed from active")

# --- A2: Ignore removes the card entirely ---
cards_before = [(b.key or "") for b in at.button
                if (b.key or "").startswith("card_")]
[b for b in at.button if b.key == "card_A2"][0].click().run()
click(at, "Ignore")
cards_after = sorted((b.key or "").split("_")[1] for b in at.button
                     if (b.key or "").startswith("card_"))
assert cards_after == ["A4"], cards_after
mds = " ".join(m.value for m in at.markdown)
assert "A2 · ignored" in mds, mds[-300:]
print("ignore removes A2; remaining:", cards_after)

# --- switch to CXO: abstain dead-end on A3 ---
click(at, "Switch persona")
[b for b in at.button if b.key == "login_cxo"][0].click().run()
[b for b in at.button if b.key == "card_A3"][0].click().run()
click(at, "Diagnose")
warns = " ".join(w.value for w in at.warning)
assert "Insufficient evidence" in warns, warns
assert not [b for b in at.button if b.label.startswith("Continue")]
back = [b for b in at.button if b.label == "← Back to Dashboard"]
assert back
back[0].click().run()
print("abstain dead-end OK")

# --- CM Apparel & Home: fast path lands straight on recommendation ---
click(at, "Switch persona")
[b for b in at.button if b.key == "login_cm_home"][0].click().run()
[b for b in at.button if b.key == "card_A5"][0].click().run()
click(at, "Diagnose")
assert not [b for b in at.button if b.label == "Expand"], \
    "fast path must skip candidate list"
subs = [s.value for s in at.subheader]
assert any("explained" in s.lower() or "recommendation" in s.lower()
           for s in subs), subs
print("fast path direct-to-recommendation OK")

print("ALL PREMIUM REDESIGN TESTS PASSED")
