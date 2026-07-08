"""
Tests for playbook sync/diff — the "SOP changed, update the playbook safely" flow.

The property that matters: a purely cosmetic change on a non-gate step is safe to
auto-apply, but ANY change touching a compliance gate must route to a human.
"""

from __future__ import annotations

import json
from pathlib import Path

from playbook_forge.schema import Playbook
from playbook_forge.sync import diff_playbooks

_REF = Path(__file__).resolve().parent.parent / "examples" / "block_card_playbook.json"


def _base() -> Playbook:
    return Playbook.model_validate(json.loads(_REF.read_text()))


def test_no_change_is_empty():
    diff = diff_playbooks(_base(), _base())
    assert diff.is_empty()
    assert not diff.needs_human_review()


def test_cosmetic_nongate_change_is_auto_safe():
    base = _base()
    v2 = base.model_copy(deep=True)
    for s in v2.steps:
        if s.id == "collect_reason":  # a non-gate step (no compliance_tag)
            s.agent_prompt = "Politely ask why they want the card blocked and note it."
    diff = diff_playbooks(base, v2)
    assert not diff.is_empty()
    assert not diff.needs_human_review(), "a cosmetic non-gate change should be auto-safe"


def test_gate_change_needs_human_review():
    base = _base()
    d = base.model_dump()
    # Add a new mandatory approval gate and wire it into place_block.
    d["steps"].append({
        "id": "manager_approval", "type": "confirm", "title": "Manager approval",
        "agent_prompt": "Obtain manager approval before blocking.", "required": True,
        "compliance_tag": "DUAL-CONTROL", "preconditions": ["verify_identity"],
        "next": None, "branches": [], "source_citation": None,
    })
    for s in d["steps"]:
        if s["id"] == "place_block":
            s["preconditions"] = ["verify_identity", "confirm_otp", "manager_approval"]
    v3 = Playbook.model_validate(d)

    diff = diff_playbooks(base, v3)
    assert diff.needs_human_review()
    assert any(c.step_id == "manager_approval" and c.change == "added" for c in diff.gate_changes)


def test_removing_a_gate_needs_review():
    base = _base()
    d = base.model_dump()
    d["steps"] = [s for s in d["steps"] if s["id"] != "confirm_otp"]
    for s in d["steps"]:
        s["preconditions"] = [p for p in s["preconditions"] if p != "confirm_otp"]
        if s.get("next") == "confirm_otp":
            s["next"] = "place_block"
    v = Playbook.model_validate(d)
    diff = diff_playbooks(base, v)
    assert diff.needs_human_review()
    assert any(c.step_id == "confirm_otp" and c.change == "removed" for c in diff.changes)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("all sync tests passed")
