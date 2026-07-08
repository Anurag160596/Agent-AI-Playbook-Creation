"""
Tests for the run-time engine and the evaluation harness.

The headline test is `test_adversarial_agent_cannot_skip_the_gate`: it proves the
safety property that justifies the whole run-time design — an agent that actively
tries to skip a compliance gate is stopped by the engine.

Run with:  PYTHONPATH=. python tests/test_engine.py   (or)  python -m pytest -q
"""

from __future__ import annotations

import json
from pathlib import Path

from playbook_forge.agent import AdversarialPolicy, CompliantPolicy
from playbook_forge.engine import Engine
from playbook_forge.schema import Playbook
from playbook_forge.simulator import run_scenario

_REF = Path(__file__).resolve().parent.parent / "examples" / "block_card_playbook.json"


def _playbook() -> Playbook:
    return Playbook.model_validate(json.loads(_REF.read_text()))


def test_engine_blocks_out_of_order_action():
    """Directly ask the engine to place the block first thing. It must refuse."""
    engine = Engine(_playbook())
    state = engine.start()
    result = engine.complete(state, "place_block")
    assert not result.ok
    assert "confirm_otp" in result.reason
    assert "place_block" not in state.completed  # nothing happened


def test_engine_allows_correct_order():
    engine = Engine(_playbook())
    state = engine.start()
    for step in ["verify_identity", "collect_reason", "confirm_otp", "place_block"]:
        assert engine.complete(state, step).ok, f"{step} should have been allowed"
    assert state.completed[:4] == ["verify_identity", "collect_reason", "confirm_otp", "place_block"]


def test_compliant_scenario_passes():
    report = run_scenario(_playbook(), CompliantPolicy(), "compliant")
    assert report.passed
    assert not report.gate_violations
    assert not report.outstanding_gates


def test_adversarial_agent_cannot_skip_the_gate():
    """The whole point: a misbehaving agent still cannot bypass the OTP gate."""
    report = run_scenario(_playbook(), AdversarialPolicy(), "adversarial")
    # The engine blocked at least once (the skip attempt)...
    assert report.blocked_attempts, "expected the engine to block the skip attempt"
    # ...no gate was ever actually violated...
    assert not report.gate_violations
    # ...and the run still finished with every required gate satisfied.
    assert report.finished
    assert not report.outstanding_gates
    assert "confirm_otp" in report.completed
    assert report.passed


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("all engine tests passed")
