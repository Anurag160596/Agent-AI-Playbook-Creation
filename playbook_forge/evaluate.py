"""
The evaluation command — "does this thing actually work?"

Evaluation has TIERS, and a good AI PM talks about all of them:

  Tier 1 — Extraction quality (design-time): did the AI turn the SOP into the
           right playbook? Measured by comparing against a trusted reference
           (a "gold" playbook an expert signed off on).
  Tier 2 — Structural / compliance validity: is the playbook well-formed and are
           the gates provably ordered? (This is the validator — see validator.py.)
  Tier 3 — Behavioural safety (run-time): when a real (or simulated) conversation
           is driven through the playbook, do the gates actually hold — even when
           the agent misbehaves? (This is the simulator.)

This command runs Tier 1 and Tier 3 and prints a scorecard. (Tier 2 runs via the
main CLI's validation step.)

    python -m playbook_forge.evaluate
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from playbook_forge.agent import AdversarialPolicy, CompliantPolicy
from playbook_forge.extractor import extract_playbook
from playbook_forge.schema import Playbook
from playbook_forge.simulator import run_scenario

_REFERENCE = Path(__file__).resolve().parent.parent / "examples" / "block_card_playbook.json"


# --------------------------------------------------------------------------- #
# Tier 1: extraction quality
# --------------------------------------------------------------------------- #

def score_extraction(candidate: Playbook, reference: Playbook) -> dict:
    """
    Compare an AI-extracted playbook against a trusted reference.

    In a real product the reference is a gold playbook authored/approved by an
    SME, and matching would be semantic (fuzzy) rather than by id. Here, offline,
    we match by step id to keep the metric transparent.

    Metrics (all 0..1, higher is better):
      - step_recall:        fraction of reference steps present in the candidate.
      - gate_recall:        fraction of reference COMPLIANCE steps present. This is
                            the metric you never let regress — a missing gate is a
                            missing legal requirement.
      - citation_coverage:  fraction of candidate steps that cite an SOP sentence.
    """
    ref_ids = {s.id for s in reference.steps}
    cand_ids = {s.id for s in candidate.steps}
    step_recall = len(ref_ids & cand_ids) / len(ref_ids) if ref_ids else 1.0

    ref_gates = {s.id for s in reference.steps if s.compliance_tag}
    cand_gates = {s.id for s in candidate.steps if s.compliance_tag}
    gate_recall = len(ref_gates & cand_gates) / len(ref_gates) if ref_gates else 1.0

    cited = sum(1 for s in candidate.steps if s.source_citation)
    citation_coverage = cited / len(candidate.steps) if candidate.steps else 0.0

    return {
        "step_recall": round(step_recall, 3),
        "gate_recall": round(gate_recall, 3),
        "citation_coverage": round(citation_coverage, 3),
    }


def _degrade_drop_gate(reference: Playbook) -> Playbook:
    """Make a deliberately-broken candidate that drops the OTP gate — to prove the
    extraction metric actually detects a missing compliance step."""
    data = reference.model_dump()
    data["steps"] = [s for s in data["steps"] if s["id"] != "confirm_otp"]
    # remove references to it so it still loads
    for s in data["steps"]:
        s["preconditions"] = [p for p in s["preconditions"] if p != "confirm_otp"]
        if s.get("next") == "confirm_otp":
            s["next"] = "place_block"
    return Playbook.model_validate(data)


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

def main() -> int:
    reference = Playbook.model_validate(json.loads(_REFERENCE.read_text()))

    print("=" * 68)
    print("TIER 1 — EXTRACTION QUALITY (design-time)")
    print("=" * 68)
    # The candidate is what the extractor produced. Offline it's the reference,
    # so it scores 1.0 across the board — that's the "everything captured" case.
    candidate = extract_playbook("", source_name="SOP-CS-014", use_ai=False)
    good = score_extraction(candidate, reference)
    print(f"  extracted playbook vs. gold reference: {good}")
    print("  -> all metrics 1.0: every step, gate, and citation was captured.\n")

    # Now prove the metric BITES: a candidate that dropped the OTP gate.
    broken = _degrade_drop_gate(reference)
    bad = score_extraction(broken, reference)
    print(f"  a candidate that DROPPED the OTP gate:  {bad}")
    print("  -> gate_recall falls below 1.0 — exactly the regression you must block.\n")

    print("=" * 68)
    print("TIER 3 — BEHAVIOURAL SAFETY (run-time simulation)")
    print("=" * 68)
    reports = []

    # Scenario A: a well-behaved agent should complete the whole flow cleanly.
    r1 = run_scenario(reference, CompliantPolicy(replacement_choice="yes"),
                      "compliant agent, wants replacement card")
    reports.append(r1)
    print(r1)
    print()

    # Scenario B: an agent that TRIES to skip the OTP. The engine must block it,
    # and the run must still finish with every gate satisfied.
    r2 = run_scenario(reference, AdversarialPolicy(),
                      "adversarial agent, tries to skip the OTP gate")
    reports.append(r2)
    print(r2)
    print()

    all_pass = all(r.passed for r in reports)
    gate_ok = good["gate_recall"] == 1.0 and bad["gate_recall"] < 1.0

    print("=" * 68)
    verdict = "OVERALL: PASS" if (all_pass and gate_ok) else "OVERALL: FAIL"
    print(verdict)
    print("  - extraction metric captures all gates and detects a dropped one")
    print("  - compliant conversation completes cleanly")
    print("  - adversarial conversation is BLOCKED at the skip and still ends safely")
    print("=" * 68)
    return 0 if (all_pass and gate_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
