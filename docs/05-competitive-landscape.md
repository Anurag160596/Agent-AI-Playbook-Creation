# 5. Competitive landscape

> **Sourcing & confidence.** This section is backed by vendor docs, product pages,
> and blog posts (linked at the bottom), gathered July 2026. Vendor capabilities
> in this space change *fast* (new features ship monthly). Treat this as a
> well-sourced snapshot, not a permanent spec — re-verify before quoting specifics
> in a live interview or PRD.

## The most important finding: this is NOT a greenfield idea

When we started, the pitch was "automatically turn SOPs into playbooks." After
researching the market, the honest truth is:

> **Auto-generating playbooks/agent-logic from SOP documents is already a shipping
> feature at multiple major vendors. It is closer to *table stakes* than to a
> differentiator.**

That's not bad news — it's *clarifying* news. It tells us exactly where the real,
defensible value is (spoiler: the *verification* layer, not the generation).

### Who already auto-generates playbooks from documents

| Vendor | What they ship today | Auto-gen from SOPs? | Emphasises compliance-*verification* of the result? |
|---|---|---|---|
| **Kore.ai** | "Bulk playbook creation": upload a knowledge article → **auto-generate playbooks** → *Review* status → Deploy/Publish. | **Yes — direct match** | **No** — docs show no compliance checking, no gate/ordering validation, no citation/traceability. Focus is conversion efficiency. |
| **Cresta** | "Conductor" draws from SOPs, knowledge, and millions of conversations to auto-generate a reviewable agent **blueprint** (goals, flows, test cases, knowledge refs). | **Yes** | Partial — produces test cases for review, but not framed as provable compliance gating. |
| **Genesys** | "AI Guides" uses LLMs to generate complete **agentic flows** (intents, slots, dialog logic) from process documents or prompts. | **Yes** | Not emphasised in the generation step. |
| **Decagon** | "Agent Operating Procedures (AOPs)": SOPs → modular bundles of prompts/logic/actions/rules; "AOP Copilot" defines logic in plain English. | **Yes** | Not emphasised as provable gating. |
| **Sierra** | "Ghostwriter" (launched ~Mar 2026): auto-generates agents from SOPs or transcripts. | **Yes** | Not emphasised. |
| **Ada** | "Playbooks": implement existing SOPs as multi-step flows without hand-coding. | **Yes** | Not emphasised. |
| **Cognigy** | "Knowledge AI": upload PDFs/pages → knowledge sources; positions for regulated industries. | Partial (knowledge ingestion; flows still authored) | Positions on compliance broadly, but not "prove the generated playbook's gates." |
| **NICE** | "Enlighten Autopilot Knowledge" connects KB to bots; "Copilot" generates responses from KB. | Partial (KB-grounded, less "playbook from SOP") | Runtime guidance + monitoring, not design-time gate proofs. |

**Read the last column.** Everyone can *generate*. Almost nobody, in the parts we
could see, makes the generated artifact **provably compliant and auditable** —
gate-ordering proofs, verbatim source citations, adversarial verification. That
gap is exactly what our prototype centres on (`validator.py`, the citations, and
the adversarial eval in `evaluate.py`).

## So where is the actual defensible value?

Reframe the whole product around the gap:

- **Commoditised (don't lead with this):** "We use AI to turn your SOP into a
  playbook." Kore.ai, Cresta, Genesys, Decagon, Sierra, and Ada already say this.
- **The real wedge:** **provable, auditable compliance of the generated playbook.**
  - Every step **cites** the exact SOP sentence (traceability for auditors).
  - A **deterministic validator proves** mandatory steps sit on *every* path to the
    actions they gate (not "the LLM usually gets it right").
  - An **adversarial evaluation harness** demonstrates the run-time guardrail holds
    even when the agent is pushed to skip a gate.

There's a *separate* ecosystem of "AI guardrails / AI audit / agent governance"
tools (AWS Connect guardrails, Galileo, Zenity, etc.), but those are mostly
**run-time filters + post-hoc audit logs** — not "prove this design-time playbook's
compliance gates are correctly ordered, with citations." That specific
design-time-verification niche is thin.

## What this means for the product story (and your interview answer)

The stronger, more credible pitch after this research:

> "Generating playbooks from SOPs is already table stakes — Kore.ai, Cresta,
> Genesys, Decagon and others ship it. The unmet need in **regulated** contact
> centres isn't generation speed; it's **trust**: can you *prove* the generated
> playbook is compliant, cite every step to policy, and show the gates hold under
> adversarial pressure? That verification-and-audit layer is what I built, and
> it's the part the incumbents underinvest in."

That answer shows three things interviewers reward: (1) you did real market
research, (2) you updated your thesis when the evidence contradicted it, and (3)
you found a genuinely defensible wedge instead of a me-too claim.

## How to position (two bets, now better informed)

- **Sell into vendors (component):** license the *verification* layer — the
  compliance validator + citation-based review workflow — to vendors whose
  generators already exist but lack provable compliance. You complement their
  generator rather than competing with it.
- **Own the layer (horizontal):** a vendor-neutral "compliance-grade playbook"
  product — ingest SOPs, generate, **and certify** — that exports into whichever
  assist tool the customer runs. The moat is the audit/verification credibility,
  which is hard to fake and is exactly what regulated buyers (the compliance
  officer, not just the ops leader) will pay for.

Either way, the moat is **not** "we call an LLM." It's the domain schema + the
verifiable compliance checks + the review/audit workflow.

---

## Sources

- Cresta Conductor — https://cresta.com/blog/cresta-conductor-the-agent-for-ai-agent-development
- Cresta Knowledge Agent — https://cresta.com/knowledge-agent
- Kore.ai Agent AI Playbook (bulk auto-generation) — https://docs.kore.ai/ai-for-service/agentai/agent-experience/playbook
- Genesys Copilots / AI Guides — https://www.genesys.com/capabilities/copilots and https://www.genesys.com/capabilities/ai-studio
- NICE Enlighten Autopilot Knowledge — https://help.nice-incontact.com/content/enlightenautopilotknowledge/enlightenautopilotknowledge.htm
- Decagon — From SOPs to Agent Operating Procedures — https://decagon.ai/blog/from-sops-to-agent-operating-procedures
- Ada Playbooks (SOPs → flows) — https://www.ada.cx/blog/your-next-star-service-rep-won-t-ask-for-a-desk-just-your-sops/
- Cognigy Knowledge AI — https://docs.cognigy.com/ai/agents/develop/knowledge-ai/overview
- AWS — Guardrails for contact-centre AI agents — https://aws.amazon.com/blogs/contact-center/implementing-responsible-ai-in-contact-centers-with-connect-ai-agents-guardrails/
- Galileo — AI agent compliance & audit trails — https://galileo.ai/blog/ai-agent-compliance-governance-audit-trails-risk-management

← Back to start: [`../README.md`](../README.md)
