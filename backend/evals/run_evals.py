"""Offline eval harness for the servicing agent — produces the numbers for the PPT.

Metrics:
  * Classification accuracy (per-intent + overall)
  * Mean confidence on correct vs. wrong predictions (calibration signal)
  * First-contact resolution rate: share of in-scope requests the agent fully
    resolves without a human, on the 3 supported intents.

Works with OR without a live LLM key (falls back to the keyword classifier), so
you always get slide-ready numbers.

Run:  uv run python -m evals.run_evals
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from app.agents.classifier import classify
from app.agents.graph import run_agent
from app.config import LLM_PROVIDER

DATA = Path(__file__).resolve().parent.parent / "app" / "data" / "eval_set.json"
SUPPORTED = {"fee_reversal", "limit_increase", "card_replacement"}


def classification_metrics(cases):
    total = len(cases)
    correct = 0
    per_intent = defaultdict(lambda: [0, 0])   # intent -> [correct, count]
    conf_correct, conf_wrong = [], []
    confusion = defaultdict(lambda: defaultdict(int))

    for c in cases:
        pred = classify(c["message"])
        gold = c["intent"]
        per_intent[gold][1] += 1
        confusion[gold][pred.intent.value] += 1
        if pred.intent.value == gold:
            correct += 1
            per_intent[gold][0] += 1
            conf_correct.append(pred.confidence)
        else:
            conf_wrong.append(pred.confidence)

    return {
        "overall_accuracy": round(correct / total, 3),
        "n": total,
        "per_intent_accuracy": {
            k: round(v[0] / v[1], 3) for k, v in per_intent.items()
        },
        "mean_conf_correct": round(sum(conf_correct) / len(conf_correct), 3)
        if conf_correct else None,
        "mean_conf_wrong": round(sum(conf_wrong) / len(conf_wrong), 3)
        if conf_wrong else None,
        "confusion": {k: dict(v) for k, v in confusion.items()},
    }


def resolution_metrics(cases):
    """Resolution quality on the 3 supported intents.

    Each case runs against fresh state; if the agent correctly asks for a missing
    amount, we complete the multi-turn slot-fill (a realistic member would answer).
    We also verify two safety properties: no auto-approval ever exceeds the policy
    cap, and the audit chain stays intact.
    """
    from app.audit.chain import AUDIT
    from app.mock_backend import card_system as cards

    in_scope = [c for c in cases if c["intent"] in SUPPORTED]
    resolved = handled = violations = 0
    outcomes = defaultdict(int)
    for i, c in enumerate(in_scope):
        cards.reset_seed()                       # isolate each case
        sid = f"eval-{i}"
        res = run_agent("M-1001", c["message"], session_id=sid)["resolution"]
        if res.status == "needs_info":           # complete the slot-fill follow-up
            res = run_agent("M-1001", "make it $11,000", session_id=sid)["resolution"]
        outcomes[res.status] += 1
        if res.status == "resolved":
            resolved += 1
            if c["intent"] == "limit_increase":  # safety: never over the cap
                if cards.get_member("M-1001").credit_limit - 10000 > 3000:
                    violations += 1
        if res.status in ("resolved", "escalated"):
            handled += 1                          # auto-resolved OR safely escalated
    return {
        "first_contact_resolution_rate": round(resolved / len(in_scope), 3),
        "correct_handling_rate": round(handled / len(in_scope), 3),
        "policy_violations": violations,
        "audit_integrity_intact": AUDIT.verify().get("intact", False),
        "n_in_scope": len(in_scope),
        "outcome_breakdown": dict(outcomes),
    }


def main():
    cases = json.loads(DATA.read_text())
    print(f"\n=== Servicing Agent Evals  [classifier: {LLM_PROVIDER}] ===\n")

    cm = classification_metrics(cases)
    print(f"Classification accuracy : {cm['overall_accuracy']*100:.1f}%  (n={cm['n']})")
    for k, v in cm["per_intent_accuracy"].items():
        print(f"   - {k:16} {v*100:.0f}%")
    print(f"Mean confidence (correct): {cm['mean_conf_correct']}")
    print(f"Mean confidence (wrong)  : {cm['mean_conf_wrong']}")

    rm = resolution_metrics(cases)
    print(f"\nFirst-contact resolution : {rm['first_contact_resolution_rate']*100:.1f}%"
          f"  (n={rm['n_in_scope']} in-scope)")
    print(f"Correct handling rate    : {rm['correct_handling_rate']*100:.1f}%"
          f"  (resolved or safely escalated)")
    print(f"Policy violations        : {rm['policy_violations']}")
    print(f"Audit integrity intact   : {rm['audit_integrity_intact']}")
    print(f"Outcome breakdown        : {rm['outcome_breakdown']}")

    out = {"provider": LLM_PROVIDER, "classification": cm, "resolution": rm}
    dest = Path(__file__).resolve().parent / "eval_results.json"
    dest.write_text(json.dumps(out, indent=2))
    print(f"\nSaved -> {dest}")


if __name__ == "__main__":
    main()
