# AquaPass Ranking Input Contract

## Purpose

This document defines the canonical inputs used by the AquaPass decision-aware evidence ranking engine.

The ranking layer evaluates candidate evidence according to its expected contribution to the pending decision while considering reliability, acquisition cost, acquisition time, and feasibility.

The ranking process must remain deterministic, explainable, and auditable.

---

## 1. Ranking Objective

For a pending decision, AquaPass ranks candidate evidence by estimating how useful each evidence item is for resolving the decision under current operational constraints.

The ranking is not intended to determine the final real-world action automatically.

The system produces an evidence priority recommendation that supports human decision-making.

---

## 2. Ranking Inputs

Each candidate evidence item is evaluated using five canonical dimensions:

1. Decision Value
2. Reliability
3. Feasibility
4. Cost
5. Time

All dimensions must be normalized to the range:

`0.0 – 1.0`

Higher values have different meanings depending on the dimension:

| Dimension | Higher value means |
|---|---|
| Decision Value | Greater expected impact on the pending decision |
| Reliability | Greater expected trustworthiness of the evidence |
| Feasibility | Easier / more practical to obtain |
| Cost | Greater acquisition cost |
| Time | Longer acquisition time |

Because Cost and Time are penalties, higher normalized values reduce the final ranking score.

---

## 3. Decision Value

### Definition

Decision Value represents the expected degree to which obtaining the candidate evidence could change, clarify, confirm, or materially reduce uncertainty around the pending decision.

### Range

`0.0 – 1.0`

### Interpretation

| Range | Interpretation |
|---|---|
| 0.00 – 0.19 | Very low decision relevance |
| 0.20 – 0.39 | Low decision relevance |
| 0.40 – 0.59 | Moderate decision relevance |
| 0.60 – 0.79 | High decision relevance |
| 0.80 – 1.00 | Very high decision relevance |

### Examples

A measurement that directly distinguishes between two competing hypotheses should normally have higher Decision Value than evidence that only provides general context.

---

## 4. Reliability

### Definition

Reliability represents the expected trustworthiness of the evidence source and acquisition method for the specific decision context.

### Range

`0.0 – 1.0`

### Interpretation

| Range | Interpretation |
|---|---|
| 0.00 – 0.19 | Very low reliability |
| 0.20 – 0.39 | Low reliability |
| 0.40 – 0.59 | Moderate reliability |
| 0.60 – 0.79 | High reliability |
| 0.80 – 1.00 | Very high reliability |

Reliability must not be inferred solely from evidence type.

Source provenance, measurement method, verification status, and contextual suitability should be considered when assigning the value.

---

## 5. Feasibility

### Definition

Feasibility represents how practical it is to obtain the candidate evidence under current operational conditions.

Factors may include:

- availability of the relevant actor or system;
- required equipment;
- geographic accessibility;
- operational constraints;
- authorization requirements;
- data accessibility.

### Range

`0.0 – 1.0`

### Interpretation

| Range | Interpretation |
|---|---|
| 0.00 – 0.19 | Very difficult / unlikely |
| 0.20 – 0.39 | Difficult |
| 0.40 – 0.59 | Moderately feasible |
| 0.60 – 0.79 | Feasible |
| 0.80 – 1.00 | Highly feasible |

---

## 6. Cost

### Definition

Cost represents the normalized acquisition burden associated with obtaining the candidate evidence.

The cost dimension may include:

- financial cost;
- personnel effort;
- equipment usage;
- operational resource consumption.

### Range

`0.0 – 1.0`

### Interpretation

| Range | Interpretation |
|---|---|
| 0.00 – 0.19 | Very low acquisition burden |
| 0.20 – 0.39 | Low acquisition burden |
| 0.40 – 0.59 | Moderate acquisition burden |
| 0.60 – 0.79 | High acquisition burden |
| 0.80 – 1.00 | Very high acquisition burden |

Higher Cost values reduce the final ranking score.

---

## 7. Time

### Definition

Time represents the normalized turnaround burden required to obtain usable evidence.

It refers to the expected time from evidence request to usable result.

### Range

`0.0 – 1.0`

### Interpretation

| Range | Interpretation |
|---|---|
| 0.00 – 0.19 | Very fast |
| 0.20 – 0.39 | Fast |
| 0.40 – 0.59 | Moderate |
| 0.60 – 0.79 | Slow |
| 0.80 – 1.00 | Very slow |

Higher Time values reduce the final ranking score.

Time must also be evaluated relative to the decision deadline.

---

## 8. Canonical Ranking Formula

The initial deterministic ranking model is:

`Score(e) = α·DecisionValue(e) + β·Reliability(e) + γ·Feasibility(e) − δ·Cost(e) − ε·Time(e)`

Where:

- `e` = candidate evidence item;
- `α` = Decision Value weight;
- `β` = Reliability weight;
- `γ` = Feasibility weight;
- `δ` = Cost penalty weight;
- `ε` = Time penalty weight.

The weights must be explicitly configured rather than hidden inside implementation code.

---

## 9. Determinism

Given identical:

- incident context;
- pending decision;
- candidate evidence;
- normalized input values;
- constraints;
- ranking weights;

the ranking engine must return the same ordering.

The ranking engine must not depend on random values.

---

## 10. Explainability Requirements

For every ranked candidate, the system should retain the underlying input values used to calculate the score.

The result must be explainable using the same dimensions used by the formula.

Example:

> Ranked highly because it has high decision value and reliability, can be obtained quickly, and is feasible under the current constraints.

A candidate that is not selected should also be explainable.

Example:

> Not selected because its additional decision value is lower while acquisition time and cost are higher.

---

## 11. Constraint Awareness

Ranking inputs must be evaluated together with operational constraints.

Examples:

- decision deadline;
- maximum available budget;
- available personnel;
- available equipment;
- geographic limitations;
- actor availability.

A candidate that cannot satisfy a hard constraint must not be treated as normally feasible merely because its theoretical Decision Value is high.

---

## 12. Demo Scenario

The canonical demo incident is:

`INC-FISH-001`

The pending decision is:

> What should be investigated or acted on next to determine the likely cause of the fish mortality?

The initial scenario contains:

- fish mortality reports;
- dissolved oxygen observation;
- heavy rainfall observation;
- satellite-derived anomaly.

Candidate evidence includes:

- independent field dissolved oxygen measurement;
- laboratory water chemistry testing;
- additional citizen verification.

These candidates are used to demonstrate decision-aware ranking.

---

## 13. Separation of Concerns

The ranking contract does not define:

- evidence ingestion;
- evidence-state classification;
- LLM-based gap detection;
- evidence request execution;
- human approval;
- action execution.

Those responsibilities belong to other AquaPass modules.

The ranking layer consumes structured inputs and produces a deterministic evidence priority result.

---

## 14. Auditability

The ranking engine should preserve:

- candidate evidence ID;
- incident ID;
- decision ID;
- normalized input values;
- configured weights;
- constraint context;
- final score;
- ranking position;
- explanation.

This allows the ranking decision to be reconstructed later.

---

## 15. Prototype Boundary

All numeric values used in the initial demo are prototype/simulated values unless explicitly sourced from a real system.

The ranking score is an engineering decision-support heuristic.

It must not be represented as a scientific, clinical, regulatory, or safety determination.