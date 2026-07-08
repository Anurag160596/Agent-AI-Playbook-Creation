"""
The extractor — the one place where AI actually does work.

Everything else in this project is plain, deterministic code. THIS file is where
a large language model (Claude) reads the messy human SOP and produces a
structured draft playbook that fits our schema.

The core idea (important for understanding modern AI products):
    We do NOT ask the model to "write a playbook" as free text and then try to
    parse its prose. That's fragile. Instead we use *structured outputs*: we hand
    the model our exact JSON schema and tell the API "your answer MUST be JSON
    that matches this shape." The API then constrains the model so the response
    is guaranteed-parseable JSON. This is the single most important technique for
    turning an LLM from a chatbot into a reliable component in a pipeline.

Two modes:
    - LIVE:    calls Claude if an API key is available. Real extraction.
    - OFFLINE: if there's no API key (or you pass use_ai=False), it loads the
               pre-computed block-card playbook so the rest of the pipeline still
               runs end-to-end and can be demonstrated. This is a demo
               convenience, not a substitute for the real model.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from playbook_forge.schema import Playbook

MODEL = "claude-opus-4-8"  # Anthropic's most capable model; the right default for a hard extraction task.

# The JSON Schema we hand to the API. It is derived automatically from our
# pydantic models so the two can never drift apart.
_SCHEMA = Playbook.model_json_schema()

_SYSTEM_PROMPT = """\
You convert contact-centre Standard Operating Procedures (SOPs) into structured, \
machine-readable playbooks for agent-assist software.

Rules you MUST follow:
- Break the SOP into atomic steps. Each step is exactly one of: verify, collect, \
confirm, action, branch, inform, escalate.
- Preserve ORDER and GATES. If the SOP says something must happen before an \
action (identity verification, OTP confirmation, consent), encode that as a \
`preconditions` entry AND make sure ordering is correct.
- Tag every step that exists to satisfy a regulation or policy with a short \
`compliance_tag` (e.g. KYC, OTP-2FA, PCI-DSS, DISCLOSURE).
- For every step, fill `source_citation` with the VERBATIM sentence from the SOP \
it came from. Never invent citations. If a step is implied but not written, leave \
the citation empty and mark the step optional.
- Represent decision points ("ask whether the customer wants X") as a `branch` \
step with one branch per outcome.
- Use stable, lowercase, snake_case ids like `verify_identity`.
- Do not add steps that are not supported by the SOP text.
"""

_USER_TEMPLATE = """\
Convert the following SOP into a single playbook object that matches the provided \
JSON schema. Return only the JSON object.

SOP ({source_name}):
---
{sop_text}
---
"""


def extract_playbook(
    sop_text: str,
    source_name: str = "SOP",
    use_ai: bool = True,
) -> Playbook:
    """
    Turn raw SOP text into a validated Playbook object.

    If `use_ai` is True and an API key is configured, this calls Claude. Otherwise
    it falls back to the bundled offline example so the pipeline stays runnable.
    """
    if use_ai and _has_credentials():
        return _extract_with_claude(sop_text, source_name)
    return _extract_offline(source_name)


def _has_credentials() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def _extract_with_claude(sop_text: str, source_name: str) -> Playbook:
    """
    The real call. We use the Anthropic SDK's structured-output path so the model
    is forced to return JSON matching our schema.
    """
    import anthropic  # imported lazily so offline mode needs no dependency at import time.

    client = anthropic.Anthropic()

    response = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        # Adaptive thinking lets the model reason about ordering/gates before it
        # writes the JSON — worth it for a task where correctness matters.
        thinking={"type": "adaptive"},
        output_config={
            "effort": "high",
            # Structured output: the response is constrained to this JSON schema.
            "format": {"type": "json_schema", "schema": _SCHEMA},
        },
        system=_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": _USER_TEMPLATE.format(source_name=source_name, sop_text=sop_text),
            }
        ],
    )

    # With structured output, the first text block is guaranteed-valid JSON.
    raw = next(b.text for b in response.content if b.type == "text")
    data = json.loads(raw)

    # The model doesn't know our metadata bookkeeping; stamp it ourselves.
    data.setdefault("metadata", {})
    data["metadata"].update({"source_document": source_name, "generated_by": MODEL})

    # pydantic validates: if the model produced anything off-shape, this raises.
    return Playbook.model_validate(data)


def _extract_offline(source_name: str) -> Playbook:
    """Load the bundled, pre-computed block-card playbook for demo purposes."""
    example = Path(__file__).resolve().parent.parent / "examples" / "block_card_playbook.json"
    data = json.loads(example.read_text())
    return Playbook.model_validate(data)
