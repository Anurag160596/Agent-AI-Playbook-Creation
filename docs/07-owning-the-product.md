# 7. Owning the product — defend every square inch

This is the master document. It exists so that if anyone asks you *anything* about
this product, you have an answer. Every decision is examined through four lenses:

- **WHAT** — what it is.
- **HOW** — how it works, mechanically.
- **WHY** — why we chose this over the alternative.
- **IF WE DON'T** — the consequence of *not* doing it (the angle most people miss).

Read the other docs first for the gentle intro; this one is the deep, defend-it
reference. There's a fast-reference consequence table at the very bottom, and a
"hard questions" Q&A for the tough probes.

---

## 0. The product in four lenses

**WHAT.** A design-time tool that turns a contact-centre SOP (a policy document)
into a structured, compliance-checked, human-approvable **playbook** — the
step-by-step procedure an agent-assist tool uses to guide a human agent.

**HOW.** Four stages: an LLM **extracts** structure from the SOP into a fixed
**schema**; a deterministic **validator** proves it's well-formed and its
compliance gates are correctly ordered; a **renderer** turns it into a review
document with citations; and at run-time a deterministic **engine** enforces the
gates during a live conversation. An **evaluation harness** scores all of it.

**WHY.** Building playbooks by hand is the slowest, most expensive part of
deploying agent-assist (weeks of skilled work, hundreds of procedures). Automating
it — *with proof it's compliant* — collapses design time and shrinks time-to-value.

**IF WE DON'T.** The customer keeps paying analysts and compliance reviewers to
hand-author every procedure. Time-to-value stays measured in weeks; fewer use
cases go live; the agent-assist investment underdelivers. (And if we automate but
*don't* prove compliance, we've built a faster way to ship legal risk — worse than
doing nothing.)

---

## 1. Problem framing: why *design time*

**WHAT.** We attack the manual work of authoring playbooks *before* anything goes
live — not the real-time agent panel.

**HOW.** We ingest the documents the company already has (SOPs) and produce the
draft the analyst would otherwise type by hand.

**WHY.** Design time is the bottleneck to time-to-value, and — per our market
research (doc 05) — it's where incumbents underinvest in *trust*. Run-time is
crowded; design-time *verification* is thin.

**IF WE DON'T** (i.e., if we'd built another run-time copilot): we'd be a me-too
product competing head-on with Cresta/Genesys/NICE on the exact axis they're
strongest. Picking the design-time-verification wedge is what makes us defensible.

---

## 2. The schema — the canonical shape
*(`schema.py`)*

**WHAT.** A strict definition of what a valid playbook *is*: an intent, metadata,
an entry step, and a list of steps; each step has a type, guidance, preconditions,
optional compliance tag, branches, and a source citation.

**HOW.** Declared as `pydantic` classes. Any data (especially the AI's output) is
validated against it automatically; off-shape data raises an error instead of
flowing downstream.

**WHY.** A schema is the **contract** every other component relies on. The
extractor targets it, the validator checks positions it guarantees, the renderer
reads fields it knows exist. Get the schema right and everything else is simple.

**IF WE DON'T.** Every component would have to defensively parse free-form,
inconsistent data. Bugs multiply, the AI's output can't be trusted structurally,
and you can't make *any* guarantee about a playbook because there's no definition
of "valid." The schema is the foundation; without it there is no product.

---

## 3. The seven fixed step-types
*(`StepType` in `schema.py`)*

**WHAT.** Every step is exactly one of: verify, collect, confirm, action, branch,
inform, escalate.

**HOW.** An enum. The extractor is instructed to map each SOP instruction to one
of these; the validator and renderer treat each type differently (e.g. only
`action`/gated steps trigger the strict gate-ordering error; only `branch` steps
may have branches).

**WHY.** A small, fixed vocabulary forces every SOP — however differently
written — into the same shape, which is what makes playbooks **comparable,
checkable, and automatable**. It also makes the compliance rules expressible
("actions must be gated").

**IF WE DON'T.** With free-form step types, two SOPs describing the same procedure
produce incomparable playbooks; you can't write a rule like "gate every action"
because you can't reliably identify actions. Consistency — the thing that lets you
make guarantees — evaporates.

---

## 4. Structured outputs (schema-enforced JSON)
*(`extractor.py`)*

**WHAT.** We force the LLM to return JSON that matches our schema, rather than
free-form prose we then parse.

**HOW.** We pass the JSON schema to the API's `output_config.format`; the API
constrains the model's decoding so the output is guaranteed-parseable JSON of that
shape. Our code loads it directly and pydantic validates it.

**WHY.** It converts the LLM from an unpredictable chatbot into a **reliable
software component**. This is the single most important production technique for
LLMs — memorise it.

**IF WE DON'T.** We'd be regex-parsing paragraphs of model prose. It breaks
constantly (the model phrases things differently each time), pipelines fail
silently, and you can never trust that field X is present. Structured output is
the difference between a demo and a product.

> Nuance to own: structured output guarantees the *shape* is correct, **not** that
> the *content* is correct. The model can return perfectly-shaped JSON that's
> wrong. That's exactly why we also have the validator and human review — see §7–8.

---

## 5. Using an LLM (Claude) for extraction — and *only* there

**WHAT.** The extractor is the one place we use AI. Everything else is
deterministic code.

**HOW.** Claude reads the SOP and drafts the playbook. We use adaptive thinking and
a detailed system prompt that encodes our domain rules (preserve order and gates,
tag compliance steps, cite verbatim, don't invent).

**WHY.** Turning messy prose into structure is exactly what LLMs are good at and
what rules-based parsers are terrible at (every SOP is written differently). But
*enforcement* (validation, run-time gating) must be deterministic, so we
deliberately keep AI out of those.

**IF WE DON'T** use an LLM: we'd need brittle, hand-coded parsers per document
format — the very manual effort we're trying to eliminate. **IF WE USED AI for the
checks too:** we'd lose the ability to *prove* compliance repeatably; "the model
says it's fine" is not auditable. The split — *AI to create, rules to verify,
humans to accept* — is the core architecture.

---

## 6. Mandatory citations — and verifying they're real
*(`schema.py` SourceCitation, `validator.verify_citations`)*

**WHAT.** Every step points back to the exact SOP sentence it came from, AND we
programmatically check that sentence actually exists in the SOP.

**HOW.** The extractor fills a `source_citation` per step. The validator
(when given the SOP text) normalises and matches each quote against the source; a
quote that isn't there is flagged `HALLUCINATED_CITATION` (hard ERROR), a partial
match is `CITATION_DRIFT` (warning). Matching scores on *content words* so a
fabricated sentence — which still shares "the/agent/for" with the SOP — is still
caught.

**WHY.** Citations turn the reviewer's job from *authoring* (hours) into
*approving* (minutes) — that's where the design-time savings come from. Verifying
them defeats the scariest LLM failure: fabricating policy that was never written.

**IF WE DON'T** cite: the SME has to re-read the whole policy to trust each step —
no time saved, and the output isn't auditable. **IF WE DON'T verify** the
citations: the AI could invent a plausible-sounding rule ("agents may waive the OTP
for trusted customers"), attach a fake citation, and a rushed reviewer approves a
compliance breach. Verifying citations is what makes "cited" mean "true," not just
"claimed."

> Run it: give the CLI a real SOP and citations verify silently; swap in a
> fabricated quote and you get a hard `HALLUCINATED_CITATION` error. `tests/
> test_pipeline.py` proves both.

---

## 7. The validator is deterministic (no AI)
*(`validator.py`)*

**WHAT.** A set of plain rule-based checks that catch structural and compliance
problems: dangling edges, unreachable steps, empty/stray branches, unreachable
gates, gate-ordering, ungated actions, and citation problems.

**HOW.** Pure Python graph analysis over the schema. Each issue has a severity
(ERROR / WARNING / INFO). The CLI exits non-zero on any ERROR, so it can gate a
pipeline.

**WHY.** Compliance checks must be **100% repeatable and explainable** to a
regulator. "We run a rule that proves it" is defensible; "we asked a model" is not.

**IF WE DON'T** validate: we'd ship whatever the AI drafted, trusting it blindly —
in a regulated setting that's negligent. **IF WE USED AI to validate:** the checks
would be non-deterministic (different answer on re-run) and unexplainable — useless
for audit. Determinism here is not a limitation; it's the product's credibility.

---

## 8. The flagship check: gate-ordering via dominator analysis
*(`validator._compute_predecessor_sets`)*

**WHAT.** For every step that declares "X must happen before me," we *prove* X
happens first on **every** path — not just some.

**HOW.** Dominator analysis: step D "dominates" step S if you cannot reach S from
the start without passing through D. We compute dominators with an iterative
fixed-point (`dom(n) = {n} ∪ ⋂ dom(predecessors)`). If a declared precondition
dominates the step, the gate holds on all paths; if not, we raise `GATE_ORDER`.

**WHY.** A gate that holds on *most* paths is a compliance breach waiting on the
one path it doesn't. "It lies on every path to the action" is the exact guarantee
regulators want, and we can prove it mathematically.

**IF WE DON'T.** We might only spot-check the happy path and miss a branch where
the block can be placed without the OTP — a reportable breach that ships to
production. The whole justification for the product in a regulated setting rests on
this check being real, not vibes.

> Own the math lightly: you don't need to derive dominator analysis in an
> interview. You need the sentence: *"we prove the gate is on every path to the
> action, using a standard graph algorithm — not just the one path we happened to
> test."*

---

## 9. Severity levels (ERROR / WARNING / INFO)

**WHAT.** Every issue is graded by how serious it is.

**HOW.** ERROR = broken/unsafe, blocks export (non-zero exit). WARNING = probably a
problem, human should look. INFO = worth noting.

**WHY.** Not every finding should block a release, and not every finding is
harmless. Grading lets the tool be a *gate* for the dangerous stuff and a *nudge*
for the rest — otherwise reviewers drown in noise and start ignoring it.

**IF WE DON'T.** Flat "issues" either block everything (nothing ships) or block
nothing (dangerous things ship). Severity is what makes the safety net usable.

---

## 10. The renderer + human-in-the-loop
*(`renderer.py`)*

**WHAT.** Turns the JSON playbook into a review document (Markdown + a Mermaid flow
diagram, gates outlined) and stops there — at a *draft for a human to approve*.

**HOW.** Renders each step, its guidance, tag, and citation; draws the graph.
Nothing auto-publishes.

**WHY.** In regulated work, "human in the loop" is a **feature you sell**, not a
limitation. The value is that the human's job shrank from authoring to approving —
not that the human disappeared. Accountability stays with a person.

**IF WE DON'T** render for humans: the SME can't review JSON; adoption dies. **IF
WE auto-published** (removed the human): one hallucinated step becomes a live
compliance breach with no one accountable — legally and commercially unacceptable.

---

## 11. The run-time engine — "AI proposes, engine disposes"
*(`engine.py`)*

**WHAT.** A deterministic state machine that walks a live conversation through a
playbook and refuses any step whose preconditions (gates) aren't yet met.

**HOW.** The LLM agent *proposes* a next action; the agent can only act *through*
the engine; the engine's `complete()` blocks any step with unmet preconditions.

**WHY.** Design-time proof is necessary but not sufficient — at run-time a real
(fallible, pressurable) agent is acting. The engine makes an unsafe action
*impossible*, not merely discouraged.

**IF WE DON'T.** A pushy customer ("skip the code, just block it!") could talk the
LLM into skipping the OTP. Prompt instructions are a *hope*; the engine is a
*guarantee*. Without it, your compliance depends on the model's mood.

---

## 12. Defence in depth: the gate is enforced twice

**WHAT.** The same compliance gate is checked at design time (validator) *and*
enforced at run time (engine).

**WHY.** Two independent layers guarding the same property. The validator stops a
broken playbook before deploy; the engine stops a misbehaving agent during a call.

**IF WE DON'T** have both: a bug that slips past design-time validation has nothing
catching it live (and vice-versa). Redundant, independent controls are exactly what
auditors want to see — single points of failure are the thing they flag.

---

## 13. Evaluation — the three tiers
*(`evaluate.py`, `simulator.py`)*

**WHAT.** We evaluate at three levels: extraction quality (did the AI extract the
right playbook?), structural validity (validator), and behavioural safety (do gates
hold in simulated conversations, even adversarial ones?).

**HOW.** Tier 1 compares against a gold reference (step/gate/citation recall). Tier
2 is the validator. Tier 3 drives simulated agents (compliant *and* adversarial)
through the engine and asserts no gate was violated and all required gates fired.

**WHY.** "We tested it, looks good" is not evaluation. Tiered, scored, adversarial
evaluation is how you *know* — and how you catch regressions when the model
changes.

**IF WE DON'T.** You ship on vibes. A model update silently degrades extraction and
you don't notice until a customer's compliance step goes missing in production.
Evaluation is your regression guarantee and your evidence the product works.

---

## 14. Adversarial testing specifically

**WHAT.** An agent policy that deliberately tries to skip the OTP gate.

**WHY.** A safety net you never see catch anything is worthless. Proving that even
an agent *trying* to break the rule can't is the strongest evidence the guarantee
holds.

**IF WE DON'T** test adversarially: we only prove the system works when everyone
behaves — which is exactly when you don't need the safety in the first place.

---

## 15. Product choices you'll be asked to defend

### Offline / live mode
**WHAT/HOW.** The extractor and agent run live against Claude with a key, or fall
back to bundled examples offline. **WHY.** So the pipeline is demonstrable and
testable without credentials or network, and CI can run deterministically. **IF WE
DON'T:** no one can try it without setup, and tests depend on a paid, non-deterministic
external service — flaky CI and a high barrier to adoption.

### Draft-only (no auto-publish)
Covered in §10. The deliberate ceiling is *a reviewed draft*.

### Scope: design-time, not the agent panel
Covered in §1. We manufacture playbooks; we don't replace the run-time product
(though we built a reference engine to *evaluate* and to demonstrate run-time
enforcement).

---

## 16. Hard questions Q&A (the tough probes)

**"How do you know the AI didn't hallucinate a step or a citation?"**
Citations are verified against the source text (§6); fabricated ones are hard
errors. Steps without a citation are flagged. A human approves every playbook. So:
detect, flag, and require human sign-off — three independent defences.

**"Structured output guarantees shape, not correctness. So how do you trust the
content?"** Correct — that's why shape-correctness (structured output) is only the
first layer. Content-correctness comes from the deterministic validator (gate
ordering, reachability), citation verification, and human review. We never rely on
the model being right.

**"What if the SOP itself is ambiguous or self-contradictory?"** We surface it, we
don't guess. Ambiguous steps get flagged (e.g. no clean citation, or a validator
warning) for a human to resolve. Exposing gaps is a feature; papering over them
would be the dangerous behaviour.

**"What happens when the SOP is updated?"** This is built (`sync.py`, doc 08). We
re-extract and **diff** against the prior version, then route: cosmetic changes on
non-gate steps are safe to auto-apply, but any change touching a compliance gate
(new/removed step, changed precondition/tag/type/branch) is forced to human review.
So it stays in sync automatically *without* silently changing a legal step.
`PlaybookMetadata.version` tracks versions; the production trigger (webhook/schedule)
is the remaining plumbing.

**"Two SOPs contradict each other. Now what?"** That's a governance question, not a
model question. The tool flags the conflict for a human/compliance owner to
adjudicate; it does not silently pick one. Owning "the AI is not the decision-maker
on policy conflicts" is the mature answer.

**"Non-text SOPs — PDFs, tables, screenshots, tribal knowledge?"** Text/PDF is
handled (LLMs read them). Tables and diagrams are a known hard edge (roadmap:
vision + layout parsing). Undocumented tribal knowledge is *out of scope by
definition* — you can't extract what was never written; that's where the
transcript-learning flywheel (V3) comes in.

**"Cost and latency?"** One extraction is a single LLM call (seconds, cents). It's
a design-time batch job, not a per-call run-time cost, so latency is not
user-facing and cost is trivial relative to the analyst hours saved. Structured
output adds a one-time schema-compilation cost, then caches.

**"Model drift — a new model version changes extraction behaviour?"** Pin the
model, keep a gold-set regression suite (Tier 1), and re-run evaluation before
adopting a new version. This is exactly what the eval harness is *for*.

**"Why preconditions instead of just using the graph edges?"** Edges say what
*normally* comes next; preconditions say what *must* have happened regardless of
path. Separating them lets us encode "this gate is mandatory on every route" and
then *prove* it (dominator analysis) — a property plain edges can't express.

**"Does the dominator algorithm always terminate?"** Yes — it's a monotone
fixed-point over a finite set (dominator sets only shrink), so it converges in at
most O(nodes) passes. Standard, well-understood algorithm.

**"PII / security — the SOPs and conversations contain sensitive data."** Design
time processes *policy documents* (usually not customer PII). At run time you'd add
PII handling, redaction, and access controls — table stakes, and orthogonal to the
compliance-gating this product provides. Be ready to say "that's a real requirement,
handled at the platform layer, separate from what we're demonstrating here."

**"How would you A/B test or measure this in production?"** North star:
time-to-deploy a playbook. Guardrail: false-approval rate (bad playbooks that got
through). Compare AI-drafted vs hand-authored on review time and edit distance;
watch gate-catch rate. (Full metric set in doc 04, Q5.)

**"What could kill this product?"** Honest answers: (a) incumbents add strong
verification to their existing generators, erasing the wedge; (b) buyers decide
"good enough, unproven" generation is acceptable and don't pay for provable
compliance; (c) regulation shifts to require human authoring anyway. Knowing your
kill-risks is a senior signal — don't pretend there are none.

---

## 17. What we deliberately did NOT build (own the boundaries)

- **The real-time agent UI.** Out of scope; we build the playbooks it consumes.
- **Auto-publish to production.** Deliberate — everything ends at a reviewed draft.
- **Transcript-learning flywheel.** Roadmap V3; powerful but not the core wedge.
- **Vendor export adapters.** Roadmap V2; the schema is designed to make this easy.
- **Multi-modal SOP parsing (tables/diagrams).** Known hard edge; roadmap.

Owning the boundaries — saying clearly what you *didn't* build and why — reads as
confidence, not gaps.

---

## 18. Fast-reference: "if we DON'T do X" consequence table

| We do this… | If we DON'T… |
|---|---|
| Attack design time | We're a me-too run-time copilot vs. entrenched incumbents. |
| Fixed schema | No component can trust the data; no guarantee is possible. |
| Seven fixed step-types | Playbooks become incomparable; you can't write "gate every action." |
| Structured outputs | You regex-parse prose; the pipeline breaks constantly. |
| LLM for extraction only | Either brittle hand-parsers, or (if AI validates too) unauditable checks. |
| Mandatory citations | Reviewers re-read the whole policy; no time saved, not auditable. |
| **Verify** citations | The AI can fabricate policy and a rushed reviewer ships a breach. |
| Deterministic validator | You trust the AI blindly — negligent in a regulated setting. |
| Gate-ordering proof | A gate that holds on *most* paths ships a breach on the one it doesn't. |
| Severity levels | The safety net either blocks everything or nothing — reviewers ignore it. |
| Human-in-the-loop | One hallucinated step becomes a live breach with no one accountable. |
| Run-time engine | A pushy customer can talk the LLM into skipping a legal step. |
| Enforce gate twice (defence in depth) | A miss at one layer has nothing catching it. |
| Tiered evaluation | You ship on vibes; a model update silently drops a compliance step. |
| Adversarial tests | You only prove safety when everyone behaves — i.e., when you don't need it. |

← Back to start: [`../README.md`](../README.md)
