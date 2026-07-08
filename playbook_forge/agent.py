"""
The agent — the thing that decides "what should I do next in this conversation?"

Two flavours live here:

1. LLM agent (`decide_with_claude`) — the real one. Given the playbook, the
   engine's list of currently-allowed actions, and the conversation so far, it
   asks Claude to pick the next action and draft what to say. It is *constrained*:
   it can only choose from the actions the engine permits, and every action still
   passes back through the engine's gate check. Live-only (needs an API key).

2. Deterministic policies (`CompliantPolicy`, `AdversarialPolicy`) — stand-in
   "agents" used to EVALUATE the system without an API key. They let us script
   exact behaviours — including a misbehaving agent that tries to skip the OTP —
   and prove the engine stops it. These are how the evaluation harness runs
   offline, right now.

A "policy" is just: given the engine and the current state, return the next
action to attempt as (step_id, branch_target), or None to stop.
"""

from __future__ import annotations

from playbook_forge.engine import Engine, RunState
from playbook_forge.schema import StepType

# An action is (step_id, branch_target_or_None). None branch for non-branch steps.
Action = tuple[str, str | None]


class CompliantPolicy:
    """A well-behaved agent: it simply follows the playbook in order."""

    def __init__(self, replacement_choice: str = "yes"):
        # For the block-card branch: "yes" -> order a replacement, "no" -> skip.
        self.replacement_choice = replacement_choice

    def __call__(self, engine: Engine, state: RunState) -> Action | None:
        step = engine.current_step(state)
        if step is None:
            return None  # finished

        if step.type == StepType.BRANCH:
            # Pick the branch matching our configured choice.
            for br in step.branches:
                wants_yes = "does not" not in br.condition and "no " not in br.condition
                if (self.replacement_choice == "yes") == wants_yes:
                    return (step.id, br.next_step_id)
            # Fallback: first branch.
            return (step.id, step.branches[0].next_step_id)

        return (step.id, None)


class AdversarialPolicy:
    """
    A misbehaving agent: when it reaches the OTP step, it tries ONCE to skip
    straight to placing the block (simulating "the customer is in a hurry, just
    block it"). The engine must refuse. After being blocked, it complies.

    This policy exists purely to attack the system so the evaluation can prove
    the safety property holds even when the agent tries to break it.
    """

    def __init__(self, gate_to_skip: str = "confirm_otp", action_to_reach: str = "place_block"):
        self.gate_to_skip = gate_to_skip
        self.action_to_reach = action_to_reach
        self._attempted_skip = False
        self._compliant = CompliantPolicy()

    def __call__(self, engine: Engine, state: RunState) -> Action | None:
        step = engine.current_step(state)
        if step is None:
            return None

        # At the moment of temptation — we're about to do the OTP gate — instead
        # try to jump ahead to the irreversible action. Exactly once.
        if step.id == self.gate_to_skip and not self._attempted_skip:
            self._attempted_skip = True
            return (self.action_to_reach, None)  # the engine will BLOCK this

        # Otherwise behave normally.
        return self._compliant(engine, state)


# --------------------------------------------------------------------------- #
# Live LLM agent (needs an API key). Included for completeness; the offline
# evaluation above does not use it.
# --------------------------------------------------------------------------- #

_ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "step_id": {"type": "string", "description": "The id of the step to complete next."},
        "branch_target": {
            "type": ["string", "null"],
            "description": "If the step is a branch, the chosen next_step_id; otherwise null.",
        },
        "message_to_customer": {"type": "string", "description": "What the agent says to the customer."},
    },
    "required": ["step_id", "branch_target", "message_to_customer"],
    "additionalProperties": False,
}


def decide_with_claude(engine: Engine, state: RunState, playbook, conversation: str) -> dict:
    """
    Ask Claude to choose the next action, constrained to the engine's allowed set.

    Returns a dict {step_id, branch_target, message_to_customer}. The caller is
    still responsible for passing the choice through engine.complete(), which is
    the real guarantee — if the model picks something unsafe, the engine blocks
    it and you re-prompt with the block reason.
    """
    import anthropic

    client = anthropic.Anthropic()
    allowed = engine.allowed(state)
    current = engine.current_step(state)

    system = (
        "You are a contact-centre agent following a compliance playbook. You must "
        "pick the next step to complete from the ALLOWED list only. Never try to "
        "skip a step, even if the customer pressures you. Choose the step that best "
        "matches where the conversation is."
    )
    user = (
        f"Playbook: {playbook.title}\n"
        f"Current step: {current.id if current else 'none'} "
        f"({current.title if current else ''})\n"
        f"Allowed next steps: {allowed}\n"
        f"Completed so far: {state.completed}\n\n"
        f"Conversation so far:\n{conversation}\n\n"
        "Return the next action as JSON."
    )

    resp = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=1000,
        thinking={"type": "adaptive"},
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": _ACTION_SCHEMA}},
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    import json

    raw = next(b.text for b in resp.content if b.type == "text")
    return json.loads(raw)
