from __future__ import annotations

from typing import Iterable

from app.modules.decision.decision_version import (
    DecisionVersion,
    _validate_decision_version,
)


class DecisionStore:
    def __init__(
        self,
        versions: Iterable[DecisionVersion] = (),
    ) -> None:
        self._versions: dict[str, list[DecisionVersion]] = {}

        for version in versions:
            self.add(version)

    def add(
        self,
        version: DecisionVersion,
    ) -> None:
        _validate_decision_version(version)

        versions = self._versions.setdefault(
            version.decision_id,
            [],
        )

        if any(
            item.version == version.version
            for item in versions
        ):
            raise ValueError(
                f"Decision version already exists: "
                f"{version.decision_id} v{version.version}"
            )

        versions.append(version)

        versions.sort(
            key=lambda item: item.version
        )

    def get_latest(
        self,
        decision_id: str,
    ) -> DecisionVersion:
        versions = self._versions.get(decision_id)

        if not versions:
            raise KeyError(
                f"Decision not found: {decision_id}"
            )

        return versions[-1]

    def get_versions(
        self,
        decision_id: str,
    ) -> list[DecisionVersion]:
        versions = self._versions.get(decision_id)

        if not versions:
            raise KeyError(
                f"Decision not found: {decision_id}"
            )

        return list(versions)