"""Quick end-to-end check of the agent + audit chain (no server needed)."""
from app.agents.graph import run_agent
from app.audit.chain import AUDIT

CASES = [
    ("M-1001", "Can you waive the $39 late fee? I paid one day late.", "s1"),
    ("M-1001", "I've been a loyal member for years, can I get a higher limit?", "s2"),
    ("M-1001", "I lost my card at the airport, I need a new one asap.", "s3"),
    ("M-2002", "Please bump my credit limit to $50,000.", "s4"),  # -> escalate
    ("M-1001", "Why is my statement so high?", "s5"),             # -> needs_info
]

for member, msg, sid in CASES:
    state = run_agent(member, msg, sid)
    c = state["classification"]
    r = state["resolution"]
    print(f"\n[{sid}] {member}: {msg}")
    print(f"   intent={c.intent.value} conf={c.confidence:.2f}")
    print(f"   -> {r.status.upper()}: {r.message}")

print("\n=== AUDIT VERIFY (intact expected) ===")
print(AUDIT.verify())
print("=== TAMPER seq 2, re-verify ===")
AUDIT._tamper_for_demo(2, {"hacked": True})
print(AUDIT.verify())
print(f"\nTotal audit entries: {len(AUDIT.entries())}")
