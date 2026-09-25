# AquaPass — Task 41: Judge-Criteria Narrative

> **Purpose:** Final evidence-backed narrative for the AquaPass competition pitch/demo.
>
> **Owner:** Sang — Data & Intelligence
>
> **Product:** AquaPass — Decision-Aware Evidence Orchestration for One Health
>
> **Track:** Track 7 — Digital Health Standards
>
> **Status:** Final Task 41 artifact

---

## 1. Executive message

### One sentence

**AquaPass identifies what evidence is missing for a pending One Health decision, ranks what is worth collecting under real-world constraints, coordinates the request, and feeds the returned evidence back into the same incident for human-approved decision updates.**

### Killer question

> **What do we need to know next, which decision will it change, and why now?**

### Killer distinction

AquaPass is not positioned as another dashboard, generic chatbot, FHIR-only integration layer, or autonomous decision maker.

The core product contribution is the **operational loop from pending decision → evidence gap → decision-aware ranking → evidence request → collection → same-incident update → human approval**.

---

# 2. The five judging criteria

The competition specification defines five judging dimensions:

| Criterion | Weight | What our evidence should prove |
|---|---:|---|
| Impact & Alignment with OneAquaHealth Mission | 30% | Environmental evidence can be connected to an actionable, traceable decision workflow |
| Innovation & Creativity | 20% | AquaPass operationalizes decision-aware evidence orchestration rather than only displaying or predicting |
| Technical Implementation / Architecture | 20% | The prototype contains real deterministic logic, constraints, evaluation, and stateful workflow components |
| Usability & User Experience | 15% | The user sees the decision, evidence gap, recommendation, WHY, request status, and update clearly |
| Feasibility & Scalability | 15% | The architecture is modular, standards-oriented, and designed to connect additional actors/systems |

Source: `AquaPass_Competition_Master_Spec_v2.md`.

---

# 3. IMPACT & ALIGNMENT — 30%

## Core story

OneAquaHealth brings together environmental, citizen, climate, sensor, and other evidence sources.

The problem AquaPass addresses is not simply:

> "Do we have data?"

It is:

> **"Given the decision we have to make, what information is still missing, and what is worth collecting now?"**

AquaPass therefore connects evidence to action without replacing the human decision-maker.

### Product loop

```text
Existing Evidence
      ↓
Incident Context
      ↓
Pending Decision
      ↓
Evidence Gap
      ↓
Decision-Aware Ranking
      ↓
Next Best Evidence
      ↓
Evidence Request
      ↓
Collection
      ↓
Returned Evidence
      ↓
Same Incident
      ↓
Decision Update
      ↓
Human Approval
```

## Concrete demo evidence

The simulated fish-mortality scenario contains:

- fish mortality;
- low dissolved oxygen;
- heavy rainfall;
- competing hypotheses;
- a pending decision;
- candidate evidence with different decision value, reliability, feasibility, cost, and time.

For the fish scenario, the gold set defines an independent field dissolved-oxygen measurement (`EV-005`) as the expected top candidate because it directly addresses the low-DO hypothesis with high decision value, strong reliability, high feasibility, low acquisition burden, and fast turnaround.

This is **simulated prototype data**, not a real-world environmental measurement.

## Impact claim to use

> "AquaPass is designed to reduce the gap between environmental evidence and operational decision-making by making the next evidence request explicit, explainable, resource-aware, and traceable."

### Do NOT say

- "AquaPass prevents environmental disasters."
- "AquaPass proves the cause of fish mortality."
- "AquaPass improves public health by X%."
- "AquaPass has been clinically/ecologically validated."

Those claims are not supported by the current prototype evaluation.

---

# 4. INNOVATION & CREATIVITY — 20%

## The innovation claim

The defensible innovation claim is:

> **AquaPass operationalizes decision-aware evidence orchestration in a One Health workflow.**

The product does not claim to have invented:

- FHIR;
- evidence graphs;
- information gain;
- next-best-evidence as a general research concept;
- AI explanations.

Instead, AquaPass combines these mechanisms around a concrete operational question:

> **Which evidence is worth collecting now for this specific pending decision, under the constraints that actually exist?**

## Why this matters

A conventional dashboard asks:

> What data do we have?

A monitoring system asks:

> What is happening?

A prediction system asks:

> What might happen?

A FHIR integration layer asks:

> How can systems exchange structured information?

AquaPass asks:

> **What evidence is worth collecting now for this specific decision, who can collect it, and what happens when it returns?**

That distinction should be the centerpiece of the innovation explanation.

---

# 5. TECHNICAL IMPLEMENTATION — 20%

## Real implementation evidence

The backend test suite currently passes:

> **104 / 104 tests**

and `python -m compileall app tests` completes successfully.

This is an implementation/test result, not a claim of scientific validation.

## Decision-aware ranking

The ranking evaluation contains:

> **10 scenarios**

The current AquaPass Top-1 agreement with the expert-defined gold set is:

> **0.90 / 90%**

The evaluation also measures a separate freshness-only baseline.

For `INC-FISH-001`:

- expected top evidence: `EV-005`;
- AquaPass top evidence: `EV-005`;
- freshness-only baseline: `EV-007`;
- therefore AquaPass matches the expected top candidate while the baseline does not.

This demonstrates the intended distinction between decision-aware ranking and a simple freshness-oriented baseline.

## Important error analysis

The evaluation deliberately does not hide disagreement.

For `INC-WATER-001`:

- expected evidence: `EV-014` — accredited laboratory contamination analysis;
- AquaPass selected: `EV-015` — field conductivity and turbidity measurement;
- the selected candidate is cheaper and faster;
- the expected candidate has higher decision value and reliability;
- the measured score margin is approximately `0.0215`.

This is useful evidence because it shows the prototype has a measurable trade-off rather than a manufactured perfect result.

### How to explain this to judges

> "Our current prototype reaches 90% Top-1 agreement on a small expert-defined gold set. The remaining disagreement is visible and analyzable: in the water scenario, the engine currently prefers a faster and cheaper field measurement over a more reliable laboratory test. We treat that as an evaluation finding, not something to hide."

## Constraint engine

The constraint layer explicitly handles:

- capability mismatch;
- location mismatch;
- actor capacity;
- busy actors;
- actors becoming available too late;
- expected results arriving after the decision deadline.

The current constraint test suite passes:

> **12 / 12 tests**

A busy actor can remain feasible but receive a soft penalty, while hard deadline/capability/location violations can make an option infeasible.

This is important because AquaPass is not merely ranking abstract evidence. It considers whether the evidence can realistically be obtained.

---

# 6. WORKFLOW EVALUATION

The project contains:

- `data/evaluation/request_metrics.csv`
- `data/evaluation/workflow_metrics_summary.csv`

The assigned workflow evaluation is intended to measure:

- time to useful evidence;
- resource usage/cost;
- unnecessary requests;
- useful evidence obtained.

### Rule for the pitch

Use the exact values from the committed evaluation artifacts.

**Do not invent or round metrics that are not present in the final artifact.**

Recommended sentence:

> "We also evaluate the operational workflow separately from ranking quality, measuring time-to-useful-evidence, resource usage, and unnecessary requests."

If exact numbers are shown on the final slide, they must come directly from the committed CSV/summary.

---

# 7. USABILITY & USER EXPERIENCE — 15%

## Decision-first hierarchy

The intended interface hierarchy is:

```text
1. Pending Decision
2. Current Evidence
3. Evidence Gap
4. Next Best Evidence
5. WHY
6. Request
7. Status
8. Decision Update
```

The user should not need to search through a large dashboard before understanding the decision.

## The key UX questions

Every recommendation should answer:

### WHAT?

> What evidence do we need next?

### WHICH DECISION?

> Which pending decision will it change?

### WHY NOW?

> Why is collecting it worth the time/resources now?

## Example WHY explanation

For a field DO measurement:

```text
Decision impact: HIGH
Reliability: HIGH
Availability: HIGH
Cost: LOW
Turnaround: FAST
Decision-window fit: YES
```

The explanation should remain grounded in the actual candidate attributes used by the scoring engine.

## Human-in-the-loop

AquaPass follows:

```text
AI / engine proposes
        ↓
Human reviews
        ↓
Confirm / Edit / Reject
        ↓
Request
```

The system is not presented as an autonomous scientific or medical authority.

---

# 8. FEASIBILITY & SCALABILITY — 15%

## Architecture

The master specification calls for a modular monolith rather than unnecessary microservices.

Conceptually:

```text
React / Next.js
      ↓
FastAPI
      ↓
PostgreSQL
      ↓
AquaPass Core
 ┌────┼─────┐
 ↓    ↓     ↓
Evidence Decision Audit
Graph   Engine  Trail
      ↓
 AI / Rules
      ↓
 FHIR / REST
      ↓
 OAH / External Systems
```

## Why this is feasible

The system separates:

- evidence representation;
- decision logic;
- ranking;
- constraints;
- orchestration;
- interoperability;
- auditability.

This allows additional evidence sources and actors to be integrated without changing the core decision concept.

## Standards

FHIR is used as the interoperability mechanism.

The positioning should be:

> **FHIR answers how information moves. AquaPass answers why that information should move now.**

Do not claim that AquaPass replaces OAH systems.

Instead:

> **AquaPass is a complementary decision layer around existing evidence and interoperable systems.**

---

# 9. LIMITATIONS — SAY THESE OPENLY

This section is essential for credibility.

### 1. Small evaluation set

The ranking evaluation currently uses 10 scenarios.

Therefore 90% Top-1 agreement is a **prototype evaluation result**, not a general performance guarantee.

### 2. Gold labels are expert-defined prototype labels

The ranking gold set provides expected top candidates and rationales. It is not a large independent scientific benchmark.

### 3. Prototype scoring

The decision-aware score is a deterministic prototype heuristic.

It is not a validated ecological probability model, clinical risk model, or causal inference model.

### 4. Simulated demo evidence

The fish-mortality scenario and its measurements are prototype/simulated evidence unless explicitly replaced by verified real-world data.

### 5. One visible ranking disagreement

The water scenario currently disagrees with the expected top candidate.

This is retained as an error-analysis result rather than hidden.

### 6. No autonomous decision authority

AquaPass proposes and explains evidence collection. Human approval remains part of the intended workflow.

---

# 10. WHAT THE JUDGE SHOULD SEE

The strongest demonstration is not a collection of screenshots.

The judge should see state change:

```text
Pending Decision
       ↓
Evidence Gap
       ↓
Next Best Evidence
       ↓
WHY
       ↓
Evidence Request
       ↓
Actor / System
       ↓
FHIR / API
       ↓
New Evidence
       ↓
SAME INCIDENT
       ↓
Decision Update
       ↓
Human Approval
```

The master specification explicitly identifies this as the core proof:

> **Recommend → Request → Collect → Return → Same Incident → Decision Update**

---

# 11. 60-SECOND JUDGE NARRATIVE

> "AquaPass starts with a decision, not just a data dashboard. When an incident has competing explanations and the current evidence is insufficient, AquaPass identifies the evidence gap and ranks what is worth collecting next. The ranking considers decision value, reliability, feasibility, cost, time, and real-world constraints. The selected candidate can become an actual evidence request, and the returned evidence is connected back to the same incident. The human then reviews the updated decision context before approving any action.
>
> In our current prototype evaluation, AquaPass reaches 90% Top-1 agreement on a 10-scenario expert-defined gold set. We also compare against a freshness-only baseline and keep the remaining disagreement visible for analysis. The backend currently passes 104 automated tests, including dedicated tests for evidence reasoning, ranking evaluation, error analysis, workflow metrics, and resource constraints.
>
> Our claim is not that the prototype has solved environmental decision-making. Our claim is that AquaPass demonstrates a concrete, interoperable workflow for asking a better question: what do we need to know next, which decision will it change, and why now?"

---

# 12. 20-SECOND CLOSING

> **"OAH connects environmental evidence. AquaPass connects evidence to decisions."**

Then:

> **"We don't ask AI to make the decision. We ask it what we need to know before humans make it."**

---

# 13. Evidence Checklist for Submission

Before calling Task 41 complete, confirm the final pitch/demo has:

- [x] Five judging criteria explicitly addressed
- [x] Ranking evaluation result: 10 scenarios / 90% Top-1
- [x] Freshness-only baseline comparison
- [x] Fish scenario example
- [x] Water disagreement and error analysis
- [x] Constraint engine evidence: 12/12 tests
- [x] Full backend test result: 104/104
- [x] Limitations stated
- [x] Simulated data clearly labeled
- [x] Human-in-the-loop stated
- [x] Decision-aware orchestration positioned as the core innovation
- [x] FHIR positioned as interoperability mechanism, not the entire innovation
- [x] Workflow metrics artifacts identified
- [x] No unsupported scientific/clinical claims

---

# 14. Task 41 Definition of Done

Task 41 is complete when this document and the final demo/pitch use the same claims:

```text
IMPACT
Evidence → decision → human-approved action

INNOVATION
Decision-aware evidence orchestration

TECHNICAL
Real deterministic ranking + constraints + evaluation

UX
Decision → gap → next evidence → WHY → request → update

FEASIBILITY
Modular architecture + interoperability + extensible actors/systems

LIMITATIONS
Small prototype evaluation + simulated data + explicit error analysis
```

**Final status: READY FOR TEAM REVIEW / PITCH INTEGRATION.**

---

## Source artifacts

- `AquaPass_Competition_Master_Spec_v2.md`
- `data/evaluation/ranking_gold.csv`
- `data/evaluation/request_metrics.csv`
- `data/evaluation/workflow_metrics_summary.csv`
- `backend/app/evaluation/ranking_evaluation.py`
- `backend/app/evaluation/ranking_error_analysis.py`
- `backend/app/modules/constraints/constraint_engine.py`
- `backend/tests/` — current full result: 104 passed
