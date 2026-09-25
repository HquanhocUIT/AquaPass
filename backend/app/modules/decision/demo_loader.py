from __future__ import annotations

import json
from pathlib import Path

from app.modules.decision.decision_store import (
    DecisionStore,
)
from app.modules.decision.decision_version import (
    create_decision_version,
)


DEFAULT_DECISION_SEED_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "demo"
    / "decision_seed.json"
)


def load_demo_decision(
    store: DecisionStore,
    path: str | Path | None = None,
) -> DecisionStore:
    """
    Load the demo decision seed into an existing DecisionStore.

    If no path is supplied, the canonical demo seed is used.

    The loader creates a validated DecisionVersion and adds it
    to the supplied store.
    """

    file_path = (
        Path(path)
        if path is not None
        else DEFAULT_DECISION_SEED_PATH
    )

    if not file_path.exists():
        raise FileNotFoundError(
            f"Decision seed file not found: {file_path}"
        )

    with file_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    decision = create_decision_version(
        decision_id=data["decision_id"],
        version=data["version"],
        incident_id=data["incident_id"],
        uncertainty=data["uncertainty"],
        uncertainty_level=data[
            "uncertainty_level"
        ].lower(),
        hypothesis_summary=data[
            "hypothesis_summary"
        ],
        triggering_evidence_id=data.get(
            "triggering_evidence_id"
        ),
    )

    store.add(decision)

    return store