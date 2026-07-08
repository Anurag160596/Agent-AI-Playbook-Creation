"""
Keeping playbooks in sync with changing SOPs.

The insight from the product owner: SOPs are not static. Policies change; sales
playbooks change constantly. When the source document changes, the playbook should
update too — ideally automatically — instead of drifting out of date until someone
notices.

But "auto-update a compliance procedure" is dangerous if done naively. The safe
design is a DIFF with a routing rule:

  - Re-extract the playbook from the new SOP.
  - Diff it against the current version.
  - **Cosmetic changes** (reworded guidance on a non-gate step) can auto-apply.
  - **Any change that touches a compliance gate** (adds/removes a step, changes a
    precondition, a compliance tag, a step type, or a branch) MUST route to a human.

So the answer to "can it update automatically?" is: *yes for the safe changes, and
it knows which ones aren't safe.* That distinction is the whole product-safety
story of dynamic sync.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from playbook_forge.schema import Playbook, Step, StepType

# Fields whose change we consider "structural / compliance-relevant" — i.e. a
# change here can alter what the procedure legally does, so it needs human review.
_GATE_SENSITIVE_FIELDS = ("type", "required", "compliance_tag", "preconditions", "branches", "next")


@dataclass
class StepChange:
    change: str            # "added" | "removed" | "modified"
    step_id: str
    fields: list[str] = field(default_factory=list)   # which fields changed (for "modified")
    touches_gate: bool = False                         # is this change compliance-relevant?

    def __str__(self) -> str:
        flag = "  ⚠ GATE" if self.touches_gate else ""
        detail = f" ({', '.join(self.fields)})" if self.fields else ""
        return f"{self.change:8} {self.step_id}{detail}{flag}"


@dataclass
class PlaybookDiff:
    changes: list[StepChange]

    @property
    def gate_changes(self) -> list[StepChange]:
        return [c for c in self.changes if c.touches_gate]

    def is_empty(self) -> bool:
        return not self.changes

    def needs_human_review(self) -> bool:
        """True if ANY change touches a compliance gate (or adds/removes a step)."""
        return any(c.touches_gate for c in self.changes)

    def routing(self) -> str:
        if self.is_empty():
            return "NO CHANGE — nothing to do."
        if self.needs_human_review():
            return "HUMAN REVIEW REQUIRED — a compliance-relevant change was detected."
        return "AUTO-APPLY SAFE — only cosmetic, non-gate changes."

    def __str__(self) -> str:
        lines = [f"Playbook diff: {len(self.changes)} change(s) — {self.routing()}"]
        for c in self.changes:
            lines.append(f"  {c}")
        return "\n".join(lines)


def _is_gate_step(step: Step | None) -> bool:
    if step is None:
        return False
    return bool(step.compliance_tag) or step.type == StepType.ACTION


def _step_field_changes(old: Step, new: Step) -> list[str]:
    """List the fields that differ between two versions of a step."""
    changed: list[str] = []
    if old.type != new.type:
        changed.append("type")
    if old.required != new.required:
        changed.append("required")
    if old.compliance_tag != new.compliance_tag:
        changed.append("compliance_tag")
    if sorted(old.preconditions) != sorted(new.preconditions):
        changed.append("preconditions")
    if old.next != new.next:
        changed.append("next")
    if [(b.condition, b.next_step_id) for b in old.branches] != \
       [(b.condition, b.next_step_id) for b in new.branches]:
        changed.append("branches")
    if old.agent_prompt.strip() != new.agent_prompt.strip():
        changed.append("agent_prompt")
    if old.title.strip() != new.title.strip():
        changed.append("title")
    return changed


def diff_playbooks(old: Playbook, new: Playbook) -> PlaybookDiff:
    """
    Compare an existing playbook to a freshly re-extracted one and classify each
    change, marking anything compliance-relevant as needing human review.
    """
    old_map, new_map = old.step_map(), new.step_map()
    changes: list[StepChange] = []

    # Added steps (in new, not in old) — always gate-sensitive: a new step in a
    # procedure changes what it does.
    for sid in new_map:
        if sid not in old_map:
            touches = _is_gate_step(new_map[sid]) or new_map[sid].required
            changes.append(StepChange("added", sid, touches_gate=touches))

    # Removed steps (in old, not in new) — removing a step, especially a gate, is
    # always something a human must approve.
    for sid in old_map:
        if sid not in new_map:
            touches = _is_gate_step(old_map[sid]) or old_map[sid].required
            changes.append(StepChange("removed", sid, touches_gate=touches))

    # Modified steps (present in both, but different).
    for sid in new_map:
        if sid in old_map:
            fields = _step_field_changes(old_map[sid], new_map[sid])
            if not fields:
                continue
            # A change touches a gate if either version is a gate step, OR any
            # gate-sensitive field changed.
            touches = (
                _is_gate_step(old_map[sid])
                or _is_gate_step(new_map[sid])
                or any(f in _GATE_SENSITIVE_FIELDS for f in fields)
            )
            changes.append(StepChange("modified", sid, fields=fields, touches_gate=touches))

    return PlaybookDiff(changes=changes)


def _demo() -> None:
    """Show the two routing outcomes on a simulated SOP update."""
    import json
    from pathlib import Path

    base = Playbook.model_validate(
        json.loads((Path(__file__).resolve().parent.parent / "examples" / "block_card_playbook.json").read_text())
    )

    print("=" * 68)
    print("SCENARIO A — SOP reworded a NON-gate step (collect_reason)")
    print("=" * 68)
    v2 = base.model_copy(deep=True)
    for s in v2.steps:
        if s.id == "collect_reason":
            s.agent_prompt = "Politely ask the customer the reason for blocking and note it."
    print(diff_playbooks(base, v2))
    print("  -> a purely cosmetic change on a non-gate step: safe to auto-apply.\n")

    print("=" * 68)
    print("SCENARIO B — SOP adds a NEW mandatory approval gate before the block")
    print("=" * 68)
    d = base.model_dump()
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
    print(diff_playbooks(base, v3))
    print("  -> a new compliance gate + changed precondition: MUST go to a human.")


if __name__ == "__main__":
    _demo()
