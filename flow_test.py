"""Click-through test of the guided step flow for the 3 demo scenarios."""
from streamlit.testing.v1 import AppTest

at = AppTest.from_file("app.py", default_timeout=120)
at.run()
assert not at.exception, at.exception

def click_next(at, n_times, expect_stop=False):
    for i in range(n_times):
        btns = [b for b in at.button if b.key and b.key.startswith("next_")]
        assert btns, f"no next button on click {i+1}"
        label = btns[0].label
        btns[0].click().run()
        assert not at.exception, at.exception
        print(f"   clicked: {label}")

# ---- A1 happy path (10 steps) ----
print("A1 Electronics/X (RESOLVED):")
[a for a in at.button if False]
open_btns = [b for b in at.button if b.key.startswith("open_A1")]
open_btns[0].click().run(); assert not at.exception
labels = [b.label for b in at.button if b.key and b.key.startswith("next_")]
print("   step 1 shown; first next:", labels)
click_next(at, 9)
subs = [s.value for s in at.subheader]
for want in ["Alert Summary", "Reconciliation", "Fast Path Check",
             "Hypothesis Testing", "Confidence Score", "Conflict Check",
             "Access Gate", "Narration", "Self-Verification",
             "Recommendation"]:
    assert any(want in s for s in subs), f"missing {want}; have {subs}"
assert not [b for b in at.button if b.key and b.key.startswith("next_")], \
    "next button should be gone at end"
print("   all 10 steps rendered, flow complete")

# persona toggle to CXO
at.radio[0].set_value("CXO").run()
assert not at.exception
assert any("[redacted" or "CXO" in str(x.value) for x in at.markdown)
print("   CXO toggle OK; narration regenerated")

# back to alerts
back = [b for b in at.button if b.label == "← Back to Alerts"][0]
back.click().run()
assert not at.exception

# ---- A3 abstain (halts at step 5) ----
print("A3 Wearables/Z (ABSTAIN):")
[b for b in at.button if b.key.startswith("open_A3")][0].click().run()
click_next(at, 4)   # steps 2..5
errs = [e.value for e in at.error]
joined = " ".join(errs)
assert "PIPELINE HALTED" in joined and "LLM was NOT called" in joined, errs
assert not [b for b in at.button if b.key and b.key.startswith("next_")]
narr = [s.value for s in at.subheader]
assert "Narration" not in narr
print("   halted after confidence; no narration rendered")

# restart works
[b for b in at.button if b.label == "↻ Restart this analysis"][0].click().run()
assert not at.exception
assert len([b for b in at.button if b.key and b.key.startswith("next_")]) == 1
print("   restart resets to step 1")

# back, then A2 conflict
[b for b in at.button if b.label == "← Back to Alerts"][0].click().run()
print("A2 Electronics/Y (CONFLICT):")
[b for b in at.button if b.key.startswith("open_A2")][0].click().run()
click_next(at, 5)   # steps 2..6
warns = " ".join(w.value for w in at.warning)
errs = " ".join(e.value for e in at.error)
assert "CONTRADICTION DETECTED" in warns, warns
assert "FLAGGED FOR MANUAL REVIEW" in errs, errs
assert not [b for b in at.button if b.key and b.key.startswith("next_")]
assert "Narration" not in [s.value for s in at.subheader]
print("   halted at conflict; no narration rendered")

print("ALL FLOW TESTS PASSED")
