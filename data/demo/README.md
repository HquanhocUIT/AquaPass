# AquaPass Demo Scenario

## Purpose

This directory contains the canonical simulated demo data used to demonstrate the AquaPass evidence-to-decision workflow.

The scenario represents a fish mortality incident in which multiple existing evidence sources are available, while additional evidence may still be needed to support the pending decision.

All records in this directory are simulated prototype data and must not be interpreted as real OneAquaHealth observations.

## Canonical Incident

- Incident ID: `INC-FISH-001`
- Title: Fish mortality after heavy rainfall
- Status: Open
- Decision ID: `DEC-FISH-001`
- Decision status: Pending
- Decision owner: `environmental_response_team`
- Decision deadline: `2026-09-17T18:00:00Z`

### Decision Question

> What should be investigated or acted on next to determine the likely cause of the fish mortality?

## Existing Evidence

The initial incident contains four known evidence records:

| Evidence ID | Type | Description | State |
|---|---|---|---|
| `EV-001` | Citizen report | Fish mortality reported along the shoreline | Known |
| `EV-002` | Sensor observation | Dissolved oxygen observation | Known |
| `EV-003` | Weather observation | Heavy rainfall before the incident | Known |
| `EV-004` | Satellite observation | Satellite-derived environmental anomaly | Known |

These records establish the initial evidence context for the incident.

## Missing / Candidate Evidence

The scenario also contains three simulated evidence candidates representing information that is not yet available:

| Evidence ID | Type | Purpose | State |
|---|---|---|---|
| `EV-005` | Field DO measurement | Independently verify dissolved oxygen | Missing |
| `EV-006` | Laboratory test | Investigate possible water chemistry / pollution explanation | Missing |
| `EV-007` | Citizen verification | Confirm the spatial extent of the reported mortality | Missing |

These records are candidates for later evidence-gap analysis and ranking. They do not represent evidence that has already been collected.

## Hypotheses

The initial scenario contains three working hypotheses:

1. Low dissolved oxygen
2. Rainfall-driven runoff or pollution input
3. Temperature-related stress

The hypothesis values in `incident_seed.json` are initial simulated context and are not clinical, regulatory, or scientific conclusions.

## Intended Workflow

The demo data is designed to support the following conceptual workflow:

```text
Existing Evidence
       |
       v
Incident Context
       |
       v
Pending Decision
       |
       v
Evidence Gap Analysis
       |
       v
Candidate Evidence
       |
       v
Decision-Aware Ranking
       |
       v
Evidence Request
       |
       v
Evidence Collection
       |
       v
Same Incident Updated
       |
       v
Human Approval
       |
       v
Action / Outcome