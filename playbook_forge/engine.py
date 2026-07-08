"""
The runtime engine — the guardrail that makes a live agent safe.

Design-time (the extractor + validator) proves a playbook is *well-formed*.
Run-time is different: now a real conversation is happening, and something has to
walk the agent through the playbook step by step AND stop them from doing the
wrong thing in the moment. That "something" is this engine.

The core safety idea — remember this for interviews:
    **The AI proposes; the engine disposes.**
    The language-model agent can *suggest* any next move it likes (it might be
    pressured by an impatient customer to "just block the card, skip the code").
    But it can only ACT through this engine, and the engine will refuse to
    complete a step until that step's preconditions (the compliance gates) are
    satisfied. So an unsafe action is impossible, not just discouraged.

This is a plain, deterministic state machine — no AI in here on purpose, for the
same reason the validator has no AI: safety enforcement must be 100% repeatable
and explainable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from playbook_forge.schema import Playbook, StepType


@dataclass
class RunState:
    """The live state of one conversation walking through one playbook."""

    current: str | None                       # the step we're currently on (soft guidance pointer)
    completed: list[str] = field(default_factory=list)   # steps finished, in order (the audit trail)
    finished: bool = False                    # has the playbook reached an end?
    log: list[str] = field(default_factory=list)         # human-readable event log


@dataclass
class ActionResult:
    """What happened when the agent tried to do something."""

    ok: bool        # was the action allowed?
    reason: str     # human-readable explanation (why allowed / why blocked)


class Engine:
    """Enforces a playbook at run-time."""

    def __init__(self, playbook: Playbook):
        self.pb = playbook
        self.steps = playbook.step_map()

    def start(self) -> RunState:
        """Begin a fresh run at the playbook's entry step."""
        return RunState(current=self.pb.entry_step_id, log=["started"])

    def allowed(self, state: RunState) -> list[str]:
        """
        Which steps is the agent *permitted* to complete right now?

        A step is allowed iff it isn't already done AND all of its preconditions
        are already completed. This single rule is the entire safety mechanism:
        an action step whose compliance gate hasn't fired simply won't appear
        here, so the agent can't legitimately do it.
        """
        return [
            sid
            for sid, s in self.steps.items()
            if sid not in state.completed
            and all(p in state.completed for p in s.preconditions)
        ]

    def complete(
        self,
        state: RunState,
        step_id: str,
        branch_target: str | None = None,
    ) -> ActionResult:
        """
        The agent asks to complete `step_id`. The engine allows it only if it's
        safe. Returns an ActionResult and, when allowed, mutates `state`.

        `branch_target` is required when completing a BRANCH step: it says which
        path the customer's answer sent us down.
        """
        step = self.steps.get(step_id)
        if step is None:
            return ActionResult(False, f"no such step '{step_id}'")

        if step_id in state.completed:
            return ActionResult(False, f"'{step_id}' is already completed")

        # --- THE GATE CHECK --------------------------------------------------
        missing = [p for p in step.preconditions if p not in state.completed]
        if missing:
            names = ", ".join(f"'{m}'" for m in missing)
            return ActionResult(
                False,
                f"BLOCKED: cannot complete '{step_id}' until {names} "
                f"{'is' if len(missing) == 1 else 'are'} completed first.",
            )

        # --- branch handling -------------------------------------------------
        if step.type == StepType.BRANCH:
            targets = [b.next_step_id for b in step.branches]
            if branch_target is None:
                return ActionResult(
                    False,
                    f"'{step_id}' is a decision point; you must choose one of: {targets}",
                )
            if branch_target not in targets:
                return ActionResult(
                    False, f"'{branch_target}' is not a valid branch of '{step_id}' ({targets})"
                )

        # --- apply -----------------------------------------------------------
        state.completed.append(step_id)
        state.log.append(f"completed {step_id}")

        # Advance the current pointer.
        if step.type == StepType.BRANCH:
            state.current = branch_target
        else:
            state.current = step.next

        if state.current is None:
            state.finished = True
            state.log.append("finished")

        return ActionResult(True, f"completed '{step_id}'")

    # --- convenience for agents/UI -------------------------------------------

    def current_step(self, state: RunState):
        """The Step object we're currently on (or None if finished)."""
        return self.steps.get(state.current) if state.current else None

    def outstanding_gates(self, state: RunState) -> list[str]:
        """Required compliance-tagged steps that have NOT yet been completed."""
        return [
            s.id
            for s in self.pb.steps
            if s.required and s.compliance_tag and s.id not in state.completed
        ]
