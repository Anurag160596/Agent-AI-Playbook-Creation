"""
The validator.

An AI can draft a playbook, but you should never *trust* a draft blindly —
especially in a regulated environment. The validator is a set of deterministic,
non-AI checks that catch structural and compliance problems before a human ever
looks at the draft. It's the safety net.

Why deterministic (rule-based) rather than "ask the AI to check itself"?
    Because in compliance you want checks that are 100% repeatable and explainable.
    A regulator will ask "how do you guarantee an action never happens before its
    verification step?" — "we ran a rule that walks the graph and proves it" is a
    great answer. "we asked a language model and it usually says it's fine" is not.

The validator returns a list of Issues. Each Issue has a severity:
    - ERROR:   the playbook is broken or unsafe. Must be fixed before use.
    - WARNING: probably a problem; a human should look.
    - INFO:    a note worth surfacing, not necessarily a problem.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from playbook_forge.schema import Playbook, StepType


class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class Issue:
    severity: Severity
    code: str          # short machine-readable code, e.g. 'GATE_ORDER'
    message: str       # human-readable explanation
    step_id: str | None = None

    def __str__(self) -> str:
        where = f" [{self.step_id}]" if self.step_id else ""
        return f"{self.severity.value:7} {self.code:16}{where} {self.message}"


def _outgoing_targets(step) -> list[str]:
    """All step ids this step can lead to (linear next + every branch target)."""
    targets: list[str] = []
    if step.next:
        targets.append(step.next)
    targets.extend(b.next_step_id for b in step.branches)
    return targets


def validate(playbook: Playbook) -> list[Issue]:
    """Run every check and return a flat list of issues (empty == clean)."""
    issues: list[Issue] = []
    steps = playbook.step_map()
    ids = set(steps)

    # --- Check 1: the entry step actually exists -------------------------------
    if playbook.entry_step_id not in ids:
        issues.append(Issue(
            Severity.ERROR, "NO_ENTRY",
            f"entry_step_id '{playbook.entry_step_id}' is not one of the defined steps.",
        ))

    # --- Check 2: every edge points at a real step -----------------------------
    # If a `next` or a branch target names a step that doesn't exist, the flow
    # would dead-end into nothing at runtime.
    for step in playbook.steps:
        for target in _outgoing_targets(step):
            if target not in ids:
                issues.append(Issue(
                    Severity.ERROR, "DANGLING_EDGE",
                    f"points to '{target}', which is not a defined step.",
                    step.id,
                ))
        for pre in step.preconditions:
            if pre not in ids:
                issues.append(Issue(
                    Severity.ERROR, "DANGLING_PRECOND",
                    f"has precondition '{pre}', which is not a defined step.",
                    step.id,
                ))

    # --- Check 3: BRANCH steps branch, others don't ----------------------------
    for step in playbook.steps:
        if step.type == StepType.BRANCH and not step.branches:
            issues.append(Issue(
                Severity.ERROR, "EMPTY_BRANCH",
                "is a branch step but defines no branches.",
                step.id,
            ))
        if step.type != StepType.BRANCH and step.branches:
            issues.append(Issue(
                Severity.WARNING, "STRAY_BRANCH",
                f"is type '{step.type.value}' but defines branches (only 'branch' steps should).",
                step.id,
            ))

    # --- Check 4: reachability -------------------------------------------------
    # Walk the graph from the entry step. Any step we never reach is dead code —
    # at best clutter, at worst a required compliance step that can never run.
    reachable: set[str] = set()
    if playbook.entry_step_id in ids:
        stack = [playbook.entry_step_id]
        while stack:
            cur = stack.pop()
            if cur in reachable:
                continue
            reachable.add(cur)
            step = steps.get(cur)
            if step:
                stack.extend(t for t in _outgoing_targets(step) if t in ids)

    for step in playbook.steps:
        if step.id not in reachable:
            # An escalation branch reached only on failure is a legitimate
            # "not on the happy path" case, so downgrade those to a warning.
            sev = Severity.WARNING if step.type == StepType.ESCALATE else Severity.WARNING
            issues.append(Issue(
                sev, "UNREACHABLE",
                "cannot be reached from the entry step (dead step).",
                step.id,
            ))
            if step.required and step.compliance_tag:
                issues.append(Issue(
                    Severity.ERROR, "UNREACHABLE_GATE",
                    f"is a REQUIRED compliance step ('{step.compliance_tag}') that can never run.",
                    step.id,
                ))

    # --- Check 5: THE BIG ONE — compliance gate ordering -----------------------
    # This is the check that justifies the whole product in a regulated setting.
    #
    # Rule: an ACTION step must never be reachable along a path where one of its
    # required compliance preconditions has not yet happened. Concretely for the
    # card example: `place_block` (action) must have `confirm_otp` (OTP-2FA gate)
    # as a precondition, and `confirm_otp` must actually occur before it on every
    # path. If the AI dropped that precondition, this catches it.
    #
    # We prove ordering by checking, for every step with preconditions, that each
    # precondition lies on *every* path from entry to that step. We approximate
    # this robustly with a "must-happen-before" (dominator-style) analysis.
    must_precede = _compute_predecessor_sets(playbook, reachable)

    for step in playbook.steps:
        if step.id not in reachable:
            continue
        for pre in step.preconditions:
            # `pre` is declared as required-before `step`. Verify that on every
            # path reaching `step`, `pre` really does appear first.
            if pre not in must_precede.get(step.id, set()):
                sev = Severity.ERROR if (step.type == StepType.ACTION or step.compliance_tag) else Severity.WARNING
                issues.append(Issue(
                    sev, "GATE_ORDER",
                    f"declares '{pre}' as a precondition, but there is a path that reaches "
                    f"'{step.id}' without passing through '{pre}' first.",
                    step.id,
                ))

    # --- Check 6: actions in a regulated playbook should be gated --------------
    # A softer, product-opinionated check: in a regulated playbook, an ACTION
    # step with no compliance-tagged precondition is suspicious — it might be an
    # unguarded irreversible operation. Surface it for a human to confirm.
    if playbook.metadata.regulated:
        for step in playbook.steps:
            if step.type != StepType.ACTION:
                continue
            has_gate = any(
                (steps.get(pre) and steps[pre].compliance_tag)
                for pre in step.preconditions
            )
            if not has_gate:
                issues.append(Issue(
                    Severity.INFO, "UNGATED_ACTION",
                    "is an action in a regulated playbook with no compliance-gated precondition. "
                    "Confirm this is intentional.",
                    step.id,
                ))

    return issues


def _compute_predecessor_sets(playbook: Playbook, reachable: set[str]) -> dict[str, set[str]]:
    """
    For each reachable step, compute the set of steps that appear on EVERY path
    from the entry step to it (its "dominators", excluding itself).

    This is a classic graph algorithm (dominator analysis). Intuition: a step D
    "dominates" step S if you cannot get from the start to S without going through
    D. If a declared precondition dominates the step, the ordering gate holds on
    every path — exactly the guarantee compliance needs.

    We compute it with a simple iterative fixed-point:
      dom(entry) = {entry}
      dom(n)     = {n} ∪ (intersection of dom(p) for all predecessors p of n)
    repeated until nothing changes.
    """
    steps = playbook.step_map()
    entry = playbook.entry_step_id

    # Build reverse edges: predecessors[n] = every step that can lead directly to n.
    predecessors: dict[str, set[str]] = {sid: set() for sid in reachable}
    for sid in reachable:
        step = steps[sid]
        for target in _outgoing_targets(step):
            if target in reachable:
                predecessors[target].add(sid)

    # Initialise: entry dominates only itself; every other node starts as "all nodes".
    all_nodes = set(reachable)
    dom: dict[str, set[str]] = {}
    for sid in reachable:
        dom[sid] = {sid} if sid == entry else set(all_nodes)

    changed = True
    while changed:
        changed = False
        for sid in reachable:
            if sid == entry:
                continue
            preds = predecessors[sid]
            if not preds:
                new = {sid}
            else:
                # Intersection of the dominators of all predecessors, plus self.
                new = set(all_nodes)
                for p in preds:
                    new &= dom[p]
                new |= {sid}
            if new != dom[sid]:
                dom[sid] = new
                changed = True

    # Return dominators *excluding the node itself* — i.e. "things that must come before me".
    return {sid: (d - {sid}) for sid, d in dom.items()}


def summarize(issues: list[Issue]) -> str:
    """A one-line headline like 'FAIL: 1 error, 2 warnings' or 'PASS: clean'."""
    errors = sum(1 for i in issues if i.severity == Severity.ERROR)
    warnings = sum(1 for i in issues if i.severity == Severity.WARNING)
    infos = sum(1 for i in issues if i.severity == Severity.INFO)
    if errors:
        head = "FAIL"
    elif warnings:
        head = "REVIEW"
    else:
        head = "PASS"
    parts = []
    if errors:
        parts.append(f"{errors} error{'s' if errors != 1 else ''}")
    if warnings:
        parts.append(f"{warnings} warning{'s' if warnings != 1 else ''}")
    if infos:
        parts.append(f"{infos} info")
    detail = ", ".join(parts) if parts else "clean"
    return f"{head}: {detail}"
