# AquaPass interface

## Direction

The UI follows the user's earlier operational workstation reference: a black navigation shell, neutral gray canvas, white data panels, square edges, and one restrained blue action color. Typography, spacing, and form controls have been enlarged and aligned for readability.

## Navigation

- `/cases` is the case register. Selecting a row opens that incident's Decision page.
- Each case section has its own URL: Decision, Evidence, Evidence map, Ranking, Workflow, and Activity.
- The active sidebar link is highlighted and marked with `aria-current="page"`.
- `/` redirects to `/cases`.

## Tokens

| Role | Value |
| --- | --- |
| Navigation and key headers | `#161616` |
| Canvas | `#f4f4f4` |
| Content surface | `#ffffff` |
| Primary text | `#242424` |
| Secondary text | `#525252` |
| Action and selection | `#0f62fe` |
| Border | `#d6d6d6` |

## Product rules

1. Show the current incident, decision deadline, and simulated-data warning on each case page.
2. Keep each task on its own route so navigation changes the page and browser history works.
3. Surface source, observation time, reliability, state, and result in the Evidence table.
4. Label scenario-based rankings and hypothesis support as prototype data.
5. Keep request transitions, FHIR ingestion, and human decision approval connected to the API.
6. Use one outline icon family in navigation, visible focus, text status labels, and responsive layouts.

The frontend reads all incident and workflow data from FastAPI. The local demo scenario is created by `backend/scripts/bootstrap_local_demo.py`.
