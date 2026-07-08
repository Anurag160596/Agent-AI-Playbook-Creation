# 4. The AI PM interview guide

This is the doc to study before interviews. It reframes everything above into the
language and frameworks interviewers expect. Each section is a question you'll
likely get, with a strong answer built from *this* project.

---

## Q1. "Walk me through this product." (the 60-second pitch)

> Contact centres run on procedures — how to block a card, dispute a charge, file
> a claim. Agent-assist tools guide human agents through these as **playbooks**.
> The problem is that building playbooks is manual: analysts read the company's
> SOPs and hand-translate each one into the tool, then compliance reviews it. For
> a big enterprise that's hundreds of procedures and weeks of work — it's the main
> thing delaying time-to-value.
>
> This product automates the **design-time** work: it ingests an SOP and produces
> a structured, ordered playbook with two things that make it trustworthy — a
> **citation** back to the exact SOP sentence for every step, and an automated
> **compliance check** that proves mandatory steps (identity verification, OTP)
> happen in the right order. The human's job shifts from authoring to approving,
> so a new use case ships in minutes instead of weeks.

Then, if they want depth, walk the four stages: extract → structure → validate →
render.

---

## Q2. "What's the core insight / why is this a good product?"

The insight: **the bottleneck isn't the runtime agent panel — it's design time.**
Everyone competes on the real-time assist experience; far fewer attack the weeks
of manual setup that gate every deployment. Automating design time compounds:
faster onboarding → more use cases live → more value → easier expansion/renewal.

Frame it with a metric: if manual authoring is ~4 hours/playbook and review-a-draft
is ~20 minutes, that's a ~90% reduction in skilled effort per playbook, multiplied
across hundreds of procedures. **That's the business case in one number.**

---

## Q3. "How do you make an LLM safe enough for a regulated use case?"

Give the three-layer answer — it shows you understand LLMs *and* risk:

1. **Constrain the output.** We use **structured outputs** (schema-enforced JSON),
   so the model can't return malformed or off-spec data. It's a component, not a
   chatbot.
2. **Verify with deterministic rules, not the model.** A separate rule-based
   validator proves compliance properties (gate ordering) that must be
   explainable and 100% repeatable for auditors. We never ask the model to grade
   its own safety.
3. **Keep a human approval gate + traceability.** Every step cites its SOP source,
   so a person can approve fast. Nothing auto-ships. The output is a *draft*.

The one-liner: **"AI for the creative step, deterministic checks for the safety
step, humans for the accountability step."**

---

## Q4. "What could go wrong? What are the failure modes?"

Interviewers love risk-awareness. Name them and your mitigation:

| Risk | What it looks like | Mitigation in this design |
|---|---|---|
| **Hallucination** | The AI invents a step or citation not in the SOP. | Require verbatim citations; a human verifies each against its quote. Steps with no citation are flagged. |
| **Dropped gate** | The AI omits/mis-orders a compliance step. | The GATE_ORDER validator proves ordering on every path and errors if broken. |
| **Ambiguous SOP** | The source policy itself is unclear/contradictory. | Surface it for human decision; don't guess. The tool exposes gaps rather than papering over them. |
| **Silent over-trust** | People rubber-stamp AI drafts. | Draft-only + review UI that centres the citation; hard ERRORs block export. |
| **Model/version drift** | A model update changes extraction behaviour. | Golden-set regression tests; pin the model; re-validate before release. |

---

## Q5. "How would you measure success?" (metrics)

Split into three tiers — a strong PM habit:

- **North Star:** *time-to-deploy a new playbook* (weeks → minutes). It captures
  the whole value prop.
- **Product/quality metrics:**
  - *Draft acceptance rate* — % of AI steps a reviewer keeps unchanged (extraction
    quality).
  - *Edit distance* — how much humans change per playbook (lower = better).
  - *Gate-catch rate* — compliance issues caught by the validator before go-live.
  - *Review time per playbook*.
- **Business metrics:** playbooks live per customer, use-case expansion,
  time-to-value at onboarding, and (downstream) agent handle-time / compliance
  adherence once the playbooks are in production.

Also mention a **guardrail metric**: *false-approval rate* (bad playbooks that got
through). You never want a speed metric to improve while safety silently degrades.

---

## Q6. "How would you build and roll this out?" (roadmap thinking)

- **V0 (this repo):** one SOP → one playbook, schema + extractor + validator +
  review view. Prove the core loop on a hard example (block card).
- **V1:** batch ingest a whole SOP library; auto-discover which intents exist;
  a review UI where SMEs approve/edit with citations side-by-side.
- **V2:** export directly into the target vendor's format (Cresta/Genesys/etc.);
  regression/golden tests; versioning and change-diffs when SOPs update.
- **V3 (the flywheel):** learn from real transcripts — compare what agents
  *actually* do to the playbook, and suggest playbook improvements. This closes
  the loop from "author from docs" to "keep in sync with reality."

Sequencing logic: nail *trust* (citations + validation) before *scale* (batch),
before *integration* (export), before *learning* (transcripts). Each unlocks the
next.

---

## Q7. "Build vs. buy? Why would a company use you vs. their vendor's tooling?"

Two honest angles:

- **As a feature inside a vendor:** this is the "playbook authoring" module that
  every agent-assist vendor needs; it accelerates *their* onboarding and is a
  competitive differentiator.
- **As a standalone/horizontal layer:** it's vendor-neutral — ingest SOPs once,
  export to whichever assist tool the customer runs. The moat is the compliance
  validation + the review workflow, not the raw LLM (anyone can call an LLM).

The defensible part is **not** "we use AI" — it's the domain-specific schema, the
verifiable compliance checks, and the human-review workflow that make the output
trustworthy in regulated settings.

> **Reality check from market research (see doc 05):** auto-generating playbooks
> from SOPs is *already shipping* at Kore.ai, Cresta, Genesys, Decagon, Sierra, and
> Ada — it's table stakes, not a wedge. On the closest match (Kore.ai) the docs
> show **no** compliance gate-validation and **no** source citations. So the honest,
> strong answer is: *"Generation is commoditised; the unmet need is provable
> compliance of the generated playbook — citations, gate-ordering proofs, and
> adversarial verification — which is the part incumbents underinvest in and the
> part I built."* Showing you researched the market and **revised your thesis** when
> evidence contradicted it is itself a strong PM signal.

---

## Q8. Traps and good habits

- **Don't over-claim autonomy.** "Fully automated compliance playbooks, no humans"
  is a *red flag* answer in regulated domains. The credible pitch is "collapses
  human effort," not "removes humans."
- **Distinguish design-time vs. run-time.** Many candidates blur these. This
  product is design-time; the agent panel is run-time. Saying it clearly signals
  domain fluency.
- **Have one crisp number** (the ~90% effort reduction) and one crisp technical
  detail (schema-enforced output + dominator-based gate check). Specificity beats
  buzzwords.

→ Next: [`05-competitive-landscape.md`](05-competitive-landscape.md)
