# 9. Become an AI PM — a curriculum built on this project

You don't become an AI Product Manager by reading theory. You become one by owning
a real AI product end-to-end and being able to explain and defend every decision in
it. **This project is that product.** This doc turns it into a course.

## How to use this

Work the modules in order. Each one has the same five parts:

- **The skill** — what capability you're building.
- **Why AI PMs specifically need it** — how it differs from generic PM work.
- **See it in this project** — the exact files/commands where the skill is made real.
- **Do this** — a hands-on exercise (you *change* or *break* something).
- **You've got it when** — a concrete self-check. If you can't do it, re-do the module.

Don't just read the "See it here" files — **run the commands and break things**.
The learning is in watching the system respond.

---

## Part 0 — What is an AI PM, really?

A normal PM ships features whose behaviour is **deterministic**: you specify it, an
engineer builds it, it does exactly that. An AI PM ships features powered by models
whose behaviour is **probabilistic**: the same input can give different outputs, the
system can be confidently wrong, and quality is a distribution, not a guarantee.

That one difference cascades into everything that makes the role distinct:

| Normal PM worries about… | AI PM *also* worries about… |
|---|---|
| Does it do what we specified? | Is it *right often enough*? How do we **measure** that? (evaluation) |
| Edge cases in logic | **Hallucination**, drift, adversarial misuse |
| "Is the feature built?" | "Do we **trust** the output enough to ship it? Who's accountable?" |
| A spec | A spec **+ an eval harness + guardrails + a human-in-loop policy** |
| Fixed behaviour | Behaviour that **changes when the model version changes** |

The three-word summary of the AI PM's job on a product like this:
> **Make the unreliable reliable enough to trust — and prove it.**

Everything below is a competency in service of that sentence.

---

## The 10 competencies (your map)

| # | Competency | Module |
|---|---|---|
| 1 | Frame the problem & find the wedge | 1 |
| 2 | Understand the AI deeply enough to make product calls | 2 |
| 3 | Design for reliability (contracts, determinism) | 3 |
| 4 | Engineer trust, safety & compliance | 4 |
| 5 | **Evaluate** — the signature AI PM skill | 5 |
| 6 | Run the lifecycle (drift, versioning, sync, monitoring) | 6 |
| 7 | Choose metrics that matter | 7 |
| 8 | Read the market, defend the moat | 8 |
| 9 | Sequence a roadmap | 9 |
| 10 | Communicate & own it (the four lenses) | 10 |

---

## Module 1 — Frame the problem & find the wedge

**The skill.** Turn a vague space ("agent assist") into a sharp, defensible problem
("automate the design-time authoring of compliance playbooks").

**Why AI PMs need it.** AI makes *many* things possible; the failure mode is
building a cool demo nobody needs. The discipline is finding the specific painful,
valuable, AI-suited problem — and the wedge competitors underinvest in.

**See it in this project.** `docs/01-what-is-agent-assist.md` (the problem),
`docs/05-competitive-landscape.md` (the wedge: generation is table stakes,
*verification* is the gap).

**Do this.** Write two paragraphs: (a) the problem in one sentence a busy exec
would nod at, (b) why *this* problem is a good fit for AI *and* has a defensible
angle. Then find one thing in doc 05 that would change your framing.

**You've got it when.** You can state the problem, the wedge, and *why the wedge is
defensible* (hint: not "we use AI") in under 45 seconds without notes.

---

## Module 2 — Enough AI to be dangerous

**The skill.** Understand LLMs, prompts, and **structured outputs** well enough to
make product decisions about them — not to train models.

**Why AI PMs need it.** You'll constantly decide "AI here, not there," "free-form or
constrained," "which failure mode matters." You can't delegate those to engineers;
they're product calls with technical substance.

**See it in this project.** `playbook_forge/extractor.py` — the *only* AI in the
system. Note three decisions: (1) structured outputs force schema-shaped JSON, (2)
the system prompt encodes domain rules, (3) adaptive thinking for a hard task.
`docs/03` §Stage-1 explains each in plain English.

**Do this.** Open `extractor.py`. Read `_SYSTEM_PROMPT`. In your own words, write
what each instruction *prevents* the model from doing wrong. Then answer: "Why do we
force JSON instead of asking for a playbook in prose?"

**You've got it when.** You can explain **structured outputs** to a non-technical
person in 3 sentences, and say the one-liner: *"structured output guarantees the
shape is right, not that the content is right"* — and why that distinction drives
the rest of the architecture.

---

## Module 3 — Design for reliability

**The skill.** Make a probabilistic component safe to build on: define a **contract**
(schema), and put **deterministic** code around the AI.

**Why AI PMs need it.** Reliability isn't something you bolt on later; it's an
architecture choice. The AI PM decides where the model is trusted and where hard code
takes over.

**See it in this project.** `playbook_forge/schema.py` (the contract) and
`playbook_forge/validator.py` (deterministic checks — no AI). `docs/07` §2, §7.

**Do this.** In `examples/block_card_playbook.json`, delete the `confirm_otp` step
and rewire `collect_reason`'s `next` to `place_block`. Run
`python -m playbook_forge.cli examples/block_card_sop.txt --no-ai`. Watch the
validator catch it. Now put it back.

**You've got it when.** You can explain *why the validator has no AI in it* — and
why that's a feature, not a limitation, in a regulated setting.

---

## Module 4 — Engineer trust, safety & compliance

**The skill.** Build the mechanisms that make an AI output *trustworthy*: citations,
citation **verification**, human-in-the-loop, run-time **guardrails**, and
defence-in-depth.

**Why AI PMs need it.** In regulated or high-stakes domains, "the model is usually
right" is not shippable. Trust is engineered, and the AI PM specs how.

**See it in this project.**
- Citations + verification: `validator.verify_citations` (`docs/07` §6).
- Human-in-the-loop: `renderer.py` stops at a *draft* (`docs/07` §10).
- Run-time guardrail: `engine.py` — "AI proposes, engine disposes" (`docs/07` §11).
- Defence in depth: the gate is checked at design time *and* enforced at run time
  (`docs/07` §12).

**Do this.** Two experiments:
1. Fabricate a citation: in the JSON, change `confirm_otp`'s quote to a sentence not
   in the SOP, re-run the CLI. Watch `HALLUCINATED_CITATION` fire.
2. Run `python -m playbook_forge.evaluate` and read the adversarial scenario — the
   agent tries to skip the OTP and the engine blocks it.

**You've got it when.** You can answer the killer interview question — *"How do you
know the AI didn't fabricate that policy?"* — in three concrete defences (verify,
flag, human sign-off), and explain why the guardrail being deterministic matters.

---

## Module 5 — Evaluation (the signature AI PM skill)

**The skill.** Prove — with numbers and adversarial tests — that the system works,
and catch regressions when the model changes.

**Why AI PMs need it.** This is *the* skill that separates AI PMs from PMs. If you
take one thing from this course: **an AI PM who can't design an eval is not an AI
PM.** You must be able to say, precisely, how you'd know the product is good.

**See it in this project.** `playbook_forge/evaluate.py` + `simulator.py`, and
`docs/06`. The three tiers: extraction quality (vs a gold reference), structural
validity (validator), behavioural safety (adversarial simulation).

**Do this.** Run `python -m playbook_forge.evaluate`. Then open `evaluate.py` and
find `score_extraction`. Add a fourth metric (e.g. "branch coverage" — fraction of
branch steps whose every branch target exists). Re-run.

**You've got it when.** You can name the three tiers, define **gate_recall** and why
it's the metric you never let regress, and explain **LLM-as-judge**, **gold sets**,
and **red-teaming** (all in `docs/06`) without looking.

---

## Module 6 — Run the lifecycle (models & content change)

**The skill.** Manage an AI product *over time*: model drift, versioning, and keeping
outputs in sync when the source changes.

**Why AI PMs need it.** AI products aren't "ship and done." The model updates; the
SOPs update. Without a lifecycle plan the product silently rots.

**See it in this project.** `playbook_forge/sync.py` (`docs/08`) — re-extract, diff,
and route: cosmetic changes auto-apply, gate-touching changes go to a human. Plus the
model-drift answer in `docs/07` §16 (pin the model, keep a regression gold set).

**Do this.** Run `python -m playbook_forge.sync`. Read the two scenarios. Then, in a
sentence each, describe how you'd *trigger* a re-sync in production (webhook?
schedule? button?) and what you'd log each time.

**You've got it when.** You can explain why "auto-update the compliance playbook when
the SOP changes" is *dangerous* naively, and how the diff-and-route design makes
"dynamic" and "safe" coexist.

---

## Module 7 — Metrics that matter

**The skill.** Pick a north star, product/quality metrics, and a **guardrail metric**
that stops you from optimising speed into unsafety.

**Why AI PMs need it.** AI metrics are subtler than clicks: you need quality
distributions, acceptance rates, and safety guardrails, not just usage.

**See it in this project.** `docs/04` Q5. North star: time-to-deploy a playbook.
Quality: draft-acceptance, edit-distance, gate-catch rate, review time. Guardrail:
false-approval rate.

**Do this.** For *this* product, write the one north-star metric, three quality
metrics, and one guardrail metric — and for each, one sentence on how you'd
instrument it (where does the number come from?).

**You've got it when.** You can explain why a **guardrail metric** exists at all (so
a speed win can't secretly increase shipped breaches) using this product as the
example.

---

## Module 8 — Market, moat & positioning

**The skill.** Research competitors, find where they're weak, and articulate a moat
that isn't "we use AI."

**Why AI PMs need it.** LLMs are commoditised — everyone can call one. The moat is
elsewhere (domain schema, verification, workflow, data). Finding it is product
strategy.

**See it in this project.** `docs/05` — the sourced finding that generation is table
stakes (Kore.ai, Cresta, Genesys, Decagon, Sierra, Ada) and the wedge is provable
compliance.

**Do this.** Pick one competitor from doc 05. In three bullets: (a) their genuine
strength, (b) the specific gap we exploit, (c) our defensible moat. Practice saying
it *without trashing them*.

**You've got it when.** You can answer *"Kore.ai already generates playbooks from
SOPs — why do you exist?"* with a crisp, evidence-based, non-defensive answer.

---

## Module 9 — Sequence a roadmap

**The skill.** Order what to build so each step unlocks the next and de-risks the
product.

**Why AI PMs need it.** With AI, sequencing is about *trust before scale*: prove the
hard thing works before you industrialise it.

**See it in this project.** `docs/04` Q6: V0 (core loop) → V1 (batch + review UI) →
V2 (vendor export, versioning/diff) → V3 (transcript-learning flywheel). Note the
logic: nail **trust** (citations + validation), then **scale**, then **integration**,
then **learning**.

**Do this.** Argue the *opposite* sequencing (integration first, trust last) and then
rebut it. Being able to defend *why this order* beats memorising the order.

**You've got it when.** You can justify the sequence with a principle ("trust before
scale"), not just a list.

---

## Module 10 — Communicate & own it (the four lenses)

**The skill.** Explain any component to an exec, an engineer, or a compliance officer
— each at the right altitude — using **What / How / Why / What-if-we-don't**.

**Why AI PMs need it.** You sit between three audiences who distrust each other's
languages. Translating — and owning the "why" and the "what breaks without it" — is
the daily job.

**See it in this project.** `docs/07` (the whole doc is this skill modelled) and its
§18 consequence table.

**Do this.** Cover the page. Pick three components at random. For each, say the four
lenses out loud. The "IF WE DON'T" line is the one that proves real ownership.

**You've got it when.** For *every* component in §18, you can give the "if we don't"
consequence from memory.

---

## Capstone — extend the product (level-up projects)

Real ownership means improving it. Pick one and build it (each maps to a real AI PM
skill):

1. **Batch mode + a review queue** — ingest many SOPs, surface drafts sorted by
   validator severity. *(Scale, workflow design.)*
2. **A sales-playbook profile** — a `regulated: false` example + a validator profile
   that checks branch coverage instead of gate ordering. *(Generalisation, doc 08.)*
3. **LLM-as-judge eval** — add a Tier-1.5 that uses a model to grade extraction
   quality against a rubric, then validate the judge against a few human labels.
   *(The frontier eval skill.)*
4. **A vendor export adapter** — emit the playbook in a second format (e.g. a generic
   flow JSON). *(Integration, distribution.)*
5. **A real live run** — wire an API key and run the extractor on a fresh SOP you
   find online; inspect where it's right and wrong. *(Ground truth with real models.)*

Ship one, then write its own `What/How/Why/If-we-don't` section. That artifact is
portfolio-grade.

---

## Putting it together — the AI PM interview

When you can do all ten modules, the interview is just narration. The arc:

1. **Pitch** (Module 1) — problem, wedge, 60 seconds.
2. **How it works** (Modules 2–4) — extract → validate → render → enforce, with the
   trust mechanisms.
3. **How you know it works** (Module 5) — the three eval tiers + adversarial proof.
4. **Over time** (Module 6) — drift, versioning, dynamic sync.
5. **Business** (Modules 7–9) — metrics, moat, roadmap.
6. **Under fire** (Module 10 + `docs/07` §16) — the hard-question Q&A.

Do the mock interview (offer at the end of this course) to rehearse the narration
until it's reflex.

---

## A 2-week study plan

| Day | Focus |
|---|---|
| 1 | Part 0 + Module 1 (framing). Read docs 01, 05. |
| 2 | Module 2 (AI basics). Read doc 03; open `extractor.py`. |
| 3 | Module 3 (reliability). Break the validator; put it back. |
| 4 | Module 4 (trust/safety). Fabricate a citation; run the adversarial eval. |
| 5–6 | Module 5 (evaluation). Run `evaluate`; add a metric. **Spend extra time here.** |
| 7 | Module 6 (lifecycle). Run `sync`; design the trigger. |
| 8 | Module 7 (metrics). Write the metric set. |
| 9 | Module 8 (market). Do the competitor drill. |
| 10 | Module 9 (roadmap). Argue the sequence. |
| 11 | Module 10 (communication). Drill the §18 table from memory. |
| 12–13 | Capstone — build one extension. |
| 14 | Full mock interview. |

---

## The one paragraph to internalise

> An AI PM makes probabilistic systems reliable enough to trust, and proves it. On
> this product that means: use the LLM only where it's strong (turning messy SOPs
> into structure), constrain it (structured outputs to a schema), verify it with
> deterministic code (gate-ordering proofs, citation checks), keep a human
> accountable (draft-only review), enforce the rules at run time (the engine), prove
> the whole thing with tiered, adversarial evaluation, and keep it alive as models
> and documents change (dynamic sync) — while competing on the part rivals
> underinvest in: provable compliance, not generation.

← Back to start: [`../README.md`](../README.md)
