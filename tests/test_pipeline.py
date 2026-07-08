"""
Tests for the playbook pipeline.

These do two jobs:
  1. Prove the happy path works (the bundled block-card playbook is well-formed).
  2. Prove the SAFETY NET works — i.e. when we deliberately break a compliance
     gate, the validator catches it. A safety net you never see catch anything
     is worthless; this test is the evidence that it does.

Run with:  python -m pytest -q     (or)     python tests/test_pipeline.py
"""

from __future__ import annotations

import copy

from playbook_forge.extractor import extract_playbook
from playbook_forge.schema import Playbook
from playbook_forge.validator import Severity, validate


def _load_good() -> Playbook:
    return extract_playbook("", source_name="SOP-CS-014", use_ai=False)


def test_good_playbook_has_no_errors():
    issues = validate(_load_good())
    errors = [i for i in issues if i.severity == Severity.ERROR]
    assert not errors, f"expected no errors, got: {[str(e) for e in errors]}"


def test_gate_order_is_enforced():
    """
    THE flagship check. We take the good playbook and simulate the AI dropping
    the OTP gate: we remove 'confirm_otp' from 'place_block's preconditions AND
    rewire the flow so the block can be placed without ever confirming the OTP.
    The validator must raise a GATE_ORDER (or UNREACHABLE_GATE) error.
    """
    data = _load_good().model_dump()

    # Rewire: collect_reason now jumps straight to place_block, skipping OTP.
    for step in data["steps"]:
        if step["id"] == "collect_reason":
            step["next"] = "place_block"
        if step["id"] == "place_block":
            # The AI still (correctly) *claims* OTP is a precondition, but the
            # flow no longer guarantees it — exactly the dangerous drift we want
            # to catch.
            pass

    broken = Playbook.model_validate(data)
    issues = validate(broken)
    codes = {i.code for i in issues}

    # place_block declares confirm_otp as a precondition, but confirm_otp is no
    # longer on every path to place_block -> GATE_ORDER. And confirm_otp itself
    # becomes unreachable (a required compliance gate that can never run).
    assert "GATE_ORDER" in codes or "UNREACHABLE_GATE" in codes, (
        f"validator failed to catch the dropped OTP gate; codes were {codes}"
    )


def test_dangling_edge_is_caught():
    data = _load_good().model_dump()
    for step in data["steps"]:
        if step["id"] == "place_block":
            step["next"] = "a_step_that_does_not_exist"
    broken = Playbook.model_validate(data)
    codes = {i.code for i in validate(broken)}
    assert "DANGLING_EDGE" in codes


if __name__ == "__main__":
    # Allow running without pytest installed.
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("all tests passed")
