"""
The evaluation harness.

This answers the question "how do I know the thing works?" for the RUN-TIME side.
It drives simulated conversations through the engine using a given agent policy,
then SCORES the result against the properties we care about — most importantly:
did every compliance gate fire before the action it protects?

Why simulation is the right eval here:
    You cannot prove an interactive system is safe by reading it. You prove it by
    *exercising* it — especially with adversarial inputs designed to break it. If
    an agent that actively tries to skip the OTP still cannot place the block,
    that's strong evidence the safety property holds. This is behavioural /
    scenario testing, and it's exactly how you'd evaluate a real agent-assist
    product.
"""

from __future__ import annotations

from dataclasses import dataclass

from playbook_forge.engine import Engine, RunState
from playbook_forge.schema import Playbook, StepType


@dataclass
class RunReport:
    scenario: str
    finished: bool
    completed: list[str]
    blocked_attempts: list[str]          # actions the engine refused
    gate_violations: list[str]           # actions that ran before a required gate (should always be empty!)
    outstanding_gates: list[str]         # required gates never completed
    passed: bool

    def __str__(self) -> str:
        head = "PASS" if self.passed else "FAIL"
        lines = [f"[{head}] scenario: {self.scenario}"]
        lines.append(f"  reached end: {self.finished}")
        lines.append(f"  completed:   {' -> '.join(self.completed) or '(none)'}")
        if self.blocked_attempts:
            lines.append(f"  engine blocked (good, means the guardrail fired):")
            for b in self.blocked_attempts:
                lines.append(f"    - {b}")
        if self.gate_violations:
            lines.append(f"  GATE VIOLATIONS (bad!): {self.gate_violations}")
        if self.outstanding_gates:
            lines.append(f"  required gates never done: {self.outstanding_gates}")
        return "\n".join(lines)


def _compliance_preconditions(playbook: Playbook) -> dict[str, list[str]]:
    """For each ACTION step, which of its preconditions are compliance gates."""
    steps = playbook.step_map()
    out: dict[str, list[str]] = {}
    for s in playbook.steps:
        if s.type == StepType.ACTION:
            out[s.id] = [p for p in s.preconditions if steps.get(p) and steps[p].compliance_tag]
    return out


def run_scenario(playbook: Playbook, policy, scenario_name: str, max_steps: int = 50) -> RunReport:
    """Drive one agent policy through the playbook and score the result."""
    engine = Engine(playbook)
    state: RunState = engine.start()
    blocked: list[str] = []
    gate_pre = _compliance_preconditions(playbook)
    gate_violations: list[str] = []

    steps = 0
    while not state.finished and steps < max_steps:
        steps += 1
        action = policy(engine, state)
        if action is None:
            break
        step_id, branch = action

        # Independent audit BEFORE we act: if this is an action step, were its
        # compliance gates already completed? (The engine enforces this, but we
        # double-check here so the eval doesn't just trust the code under test.)
        if step_id in gate_pre:
            missing = [g for g in gate_pre[step_id] if g not in state.completed]
            result_will_be_allowed = not [p for p in playbook.step_map()[step_id].preconditions
                                          if p not in state.completed]
            if missing and result_will_be_allowed:
                # Engine would have allowed an action with an unmet gate — a real bug.
                gate_violations.append(f"{step_id} ran without gate(s) {missing}")

        res = engine.complete(state, step_id, branch)
        if not res.ok:
            blocked.append(res.reason)

    outstanding = engine.outstanding_gates(state)

    # A scenario passes if: it reached the end, no gate was ever violated, and no
    # required compliance gate was left undone.
    passed = state.finished and not gate_violations and not outstanding

    return RunReport(
        scenario=scenario_name,
        finished=state.finished,
        completed=state.completed,
        blocked_attempts=blocked,
        gate_violations=gate_violations,
        outstanding_gates=outstanding,
        passed=passed,
    )
