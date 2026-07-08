"""
The canonical Playbook schema.

This is the heart of the whole system. Everything else — the AI extractor, the
validator, the renderer — exists to produce or consume objects that match the
shapes defined here.

Why a schema matters (read this if you're new to the idea):
    An SOP (Standard Operating Procedure) is written for humans. It's prose:
    paragraphs, bullet points, "if X then Y" sentences scattered around. A
    computer can't *act* on prose. So we define a strict, predictable structure —
    a "shape" — that a playbook must fit into. Once messy prose is forced into
    this shape, every downstream tool can rely on it: the validator knows exactly
    where to look for compliance gates, the renderer knows exactly how to draw
    the flow, and a runtime engine could walk it step by step.

We use `pydantic`, a Python library that lets us declare these shapes as classes
and then *validates* any data against them automatically. If the AI returns JSON
that's missing a required field or uses a wrong type, pydantic raises an error
instead of letting bad data flow silently downstream.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class StepType(str, Enum):
    """
    Every step in a playbook is one of a small, fixed set of *kinds*.

    Keeping this list short and fixed is a deliberate product decision: it forces
    every SOP, no matter how it's written, into the same vocabulary. That
    consistency is what makes playbooks comparable, auditable, and automatable.
    """

    VERIFY = "verify"      # Confirm the customer's identity or eligibility (e.g. KYC, security questions).
    COLLECT = "collect"    # Gather a piece of information from the customer (reason, account number, OTP).
    CONFIRM = "confirm"    # Get explicit agreement / acknowledgement before a consequential action.
    ACTION = "action"      # Do the actual thing in a backend system (block the card, issue a refund).
    BRANCH = "branch"      # A decision point that sends the conversation down different paths.
    INFORM = "inform"      # Tell the customer something (timelines, next steps, disclosures).
    ESCALATE = "escalate"  # Hand off to a human specialist, supervisor, or another department.


class Branch(BaseModel):
    """
    One arm of a decision point.

    A BRANCH step has several of these. Example: at "Does the customer want a
    replacement card?", one Branch is condition="customer says yes" ->
    issue_replacement, another is condition="customer says no" -> close_case.
    """

    condition: str = Field(
        ...,
        description="Plain-language description of when this path is taken, e.g. 'customer confirms the card is lost'.",
    )
    next_step_id: str = Field(
        ...,
        description="The id of the step to go to when this condition is true.",
    )


class SourceCitation(BaseModel):
    """
    A pointer back to the exact sentence in the original SOP that this step came
    from.

    This is the single most important field for *trust*. In a regulated contact
    center, a compliance reviewer will not accept an AI-generated playbook on
    faith. But if every step says "this came from line 14 of the Card Services
    SOP, which reads: '...'", the reviewer can approve in seconds instead of
    re-reading the whole policy. Citations are what turn a scary black box into
    an auditable draft.
    """

    quote: str = Field(..., description="The verbatim sentence(s) from the SOP this step is based on.")
    location: Optional[str] = Field(
        None,
        description="Where in the source it appears, e.g. 'line 14' or 'section 3.2'. Optional but strongly recommended.",
    )


class Step(BaseModel):
    """A single, atomic instruction the agent follows."""

    id: str = Field(..., description="Unique, stable identifier for this step, e.g. 'verify_identity'.")
    type: StepType = Field(..., description="Which kind of step this is (see StepType).")
    title: str = Field(..., description="Short human-readable label, e.g. 'Verify customer identity'.")
    agent_prompt: str = Field(
        ...,
        description="What the agent should actually say or do at this step, in guidance form.",
    )

    required: bool = Field(
        True,
        description="If True, this step MUST be completed. Required + compliance-tagged steps are the gates.",
    )
    compliance_tag: Optional[str] = Field(
        None,
        description="If this step exists to satisfy a regulation/policy, tag it, e.g. 'KYC', 'OTP-2FA', 'PCI-DSS'.",
    )

    preconditions: list[str] = Field(
        default_factory=list,
        description="ids of steps that MUST be completed before this step is allowed. This encodes ordering gates.",
    )

    # For linear steps, `next` points to the single following step.
    # For BRANCH steps, `next` is ignored and `branches` is used instead.
    next: Optional[str] = Field(
        None,
        description="id of the next step for a linear flow. None means this step can end the playbook.",
    )
    branches: list[Branch] = Field(
        default_factory=list,
        description="For BRANCH steps only: the possible paths out of this decision point.",
    )

    source_citation: Optional[SourceCitation] = Field(
        None,
        description="Pointer back to the SOP sentence this step came from. Enables human review.",
    )


class PlaybookMetadata(BaseModel):
    """Book-keeping about where the playbook came from and how it's governed."""

    source_document: str = Field(..., description="Name/id of the SOP this playbook was generated from.")
    regulated: bool = Field(
        True,
        description="Whether this playbook governs a regulated flow (turns on stricter gate checks).",
    )
    version: str = Field("0.1.0", description="Version of this playbook draft.")
    generated_by: str = Field(
        "playbook-forge",
        description="What produced this playbook (model name in live mode, or 'offline-demo').",
    )


class Playbook(BaseModel):
    """
    The whole thing: one intent, its metadata, and an ordered graph of steps.

    A playbook is really a *directed graph*: steps are nodes, and `next`/`branches`
    are the edges. `entry_step_id` says where to start. Thinking of it as a graph
    (not a flat checklist) is what lets us represent real-world flows with
    branches, like "reissue a card or not".
    """

    intent: str = Field(..., description="The customer intent this playbook handles, e.g. 'block_card'.")
    title: str = Field(..., description="Human-readable name, e.g. 'Block a lost or stolen card'.")
    description: str = Field("", description="One or two sentences on what this playbook is for.")
    metadata: PlaybookMetadata
    entry_step_id: str = Field(..., description="id of the first step to execute.")
    steps: list[Step] = Field(..., description="All steps in the playbook.")

    # --- convenience helpers used by the validator and renderer ---

    def step_map(self) -> dict[str, Step]:
        """Return a dict of {step_id: Step} for fast lookup."""
        return {s.id: s for s in self.steps}

    def get(self, step_id: str) -> Optional[Step]:
        """Fetch a step by id, or None if it doesn't exist."""
        return self.step_map().get(step_id)
