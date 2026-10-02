from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.core.config import Settings, settings
from app.modules.ai.gemini_client import GeminiClient, GeminiError
from app.modules.evidence.gap_detector import (
    EvidenceGap,
    EvidenceGraphRecord,
    GapPriority,
    detect_evidence_gaps,
)
from app.modules.ranking.ranking_engine import (
    EvidenceCandidate,
    RankedEvidence,
    rank_evidence,
)


@dataclass(frozen=True)
class AiRunMetadata:
    provider: str
    model: str | None
    fallback_reason: str | None = None


@dataclass(frozen=True)
class GapSuggestionResult:
    gaps: list[EvidenceGap]
    metadata: AiRunMetadata


@dataclass(frozen=True)
class RankingExplanation:
    evidence_id: str
    explanation: str
    strengths: tuple[str, ...]
    tradeoffs: tuple[str, ...]


@dataclass(frozen=True)
class RankingExplanationResult:
    ranked: list[RankedEvidence]
    explanations: list[RankingExplanation]
    metadata: AiRunMetadata


GAP_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "gaps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "evidence_id": {"type": "string"},
                    "target_hypothesis": {"type": "string"},
                    "why_missing": {"type": "string"},
                    "decision_impact": {"type": "string"},
                    "priority": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                    },
                },
                "required": [
                    "evidence_id",
                    "target_hypothesis",
                    "why_missing",
                    "decision_impact",
                    "priority",
                ],
            },
        }
    },
    "required": ["gaps"],
}


RANKING_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "explanations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "evidence_id": {"type": "string"},
                    "explanation": {"type": "string"},
                    "strengths": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "tradeoffs": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": [
                    "evidence_id",
                    "explanation",
                    "strengths",
                    "tradeoffs",
                ],
            },
        }
    },
    "required": ["explanations"],
}


def suggest_evidence_gaps(
    records: list[EvidenceGraphRecord],
    *,
    app_settings: Settings = settings,
    client: GeminiClient | None = None,
) -> GapSuggestionResult:
    fallback = detect_evidence_gaps(records)
    if not app_settings.llm_enabled:
        return GapSuggestionResult(
            gaps=fallback,
            metadata=AiRunMetadata(
                provider="deterministic_fallback",
                model=None,
                fallback_reason="LLM_ENABLED is false.",
            ),
        )

    try:
        active_client = client or GeminiClient(
            api_key=app_settings.llm_api_key or "",
            model=app_settings.llm_model,
            timeout_seconds=app_settings.llm_timeout_seconds,
        )
        payload = active_client.generate_json(
            prompt=_gap_prompt(records),
            response_schema=GAP_RESPONSE_SCHEMA,
        )
        gaps = _validated_gap_suggestions(records, payload)
        if gaps is None:
            raise GeminiError("Gemini gap response failed validation")

        return GapSuggestionResult(
            gaps=gaps,
            metadata=AiRunMetadata(
                provider="gemini",
                model=app_settings.llm_model,
            ),
        )
    except GeminiError as exc:
        return GapSuggestionResult(
            gaps=fallback,
            metadata=AiRunMetadata(
                provider="deterministic_fallback",
                model=app_settings.llm_model,
                fallback_reason=str(exc),
            ),
        )


def explain_ranking(
    candidates: list[EvidenceCandidate],
    *,
    app_settings: Settings = settings,
    client: GeminiClient | None = None,
) -> RankingExplanationResult:
    ranked = rank_evidence(candidates)
    fallback = [
        RankingExplanation(
            evidence_id=item.evidence_id,
            explanation=item.explanation,
            strengths=item.strengths,
            tradeoffs=item.tradeoffs,
        )
        for item in ranked
    ]

    if not app_settings.llm_enabled:
        return RankingExplanationResult(
            ranked=ranked,
            explanations=fallback,
            metadata=AiRunMetadata(
                provider="deterministic_fallback",
                model=None,
                fallback_reason="LLM_ENABLED is false.",
            ),
        )

    try:
        active_client = client or GeminiClient(
            api_key=app_settings.llm_api_key or "",
            model=app_settings.llm_model,
            timeout_seconds=app_settings.llm_timeout_seconds,
        )
        payload = active_client.generate_json(
            prompt=_ranking_prompt(ranked),
            response_schema=RANKING_RESPONSE_SCHEMA,
        )
        explanations = _validated_ranking_explanations(ranked, payload)
        if explanations is None:
            raise GeminiError("Gemini ranking response failed validation")

        return RankingExplanationResult(
            ranked=ranked,
            explanations=explanations,
            metadata=AiRunMetadata(
                provider="gemini",
                model=app_settings.llm_model,
            ),
        )
    except GeminiError as exc:
        return RankingExplanationResult(
            ranked=ranked,
            explanations=fallback,
            metadata=AiRunMetadata(
                provider="deterministic_fallback",
                model=app_settings.llm_model,
                fallback_reason=str(exc),
            ),
        )


def _gap_prompt(records: list[EvidenceGraphRecord]) -> str:
    graph = [
        {
            "graph_id": record.graph_id,
            "incident_id": record.incident_id,
            "decision_id": record.decision_id,
            "evidence_id": record.source_node,
            "evidence_type": record.source_type,
            "relationship": record.relationship,
            "target": record.target_node,
            "target_type": record.target_type,
            "confidence": record.confidence,
            "state": record.state,
            "rationale": record.rationale,
        }
        for record in records
    ]
    return (
        "You are the evidence-gap assistant for AquaPass. Return only JSON "
        "matching the supplied schema. Suggest missing evidence only when the "
        "input graph marks it as relationship='missing_for', state='missing', "
        "source_type='evidence', and target_type is 'hypothesis' or 'decision'. "
        "Use only evidence IDs and target nodes present in the input. Do not "
        "invent measurements, causes, IDs, or external facts. Keep each reason "
        "grounded in the input rationale and explain how the evidence could "
        "change the pending decision.\n\nInput graph:\n"
        + json.dumps(graph, ensure_ascii=False)
    )


def _ranking_prompt(ranked: list[RankedEvidence]) -> str:
    candidates = [
        {
            "evidence_id": item.evidence_id,
            "candidate_name": item.candidate_name,
            "rank": item.rank,
            "score": round(item.score, 4),
            "decision_value": item.decision_value,
            "reliability": item.reliability,
            "feasibility": item.feasibility,
            "cost": item.cost,
            "time": item.time,
            "selected": item.selected,
        }
        for item in ranked
    ]
    return (
        "You explain an AquaPass evidence ranking. Return only JSON matching "
        "the supplied schema. Preserve every evidence_id exactly, do not change "
        "rank or score, and do not introduce facts that are not in the input. "
        "Explain the ranking using the five supplied dimensions and the score. "
        "Strengths and tradeoffs must be short, grounded phrases.\n\n"
        "Ranked candidates:\n"
        + json.dumps(candidates, ensure_ascii=False)
    )


def _validated_gap_suggestions(
    records: list[EvidenceGraphRecord],
    payload: dict[str, Any],
) -> list[EvidenceGap] | None:
    allowed: dict[tuple[str, str], EvidenceGraphRecord] = {
        (record.source_node, record.target_node): record
        for record in records
        if (
            record.relationship == "missing_for"
            and record.source_type == "evidence"
            and record.target_type in {"hypothesis", "decision"}
            and record.state == "missing"
        )
    }
    raw_gaps = payload.get("gaps")
    if not isinstance(raw_gaps, list):
        return None

    gaps: list[EvidenceGap] = []
    seen: set[tuple[str, str]] = set()
    for raw in raw_gaps:
        if not isinstance(raw, dict):
            return None

        evidence_id = raw.get("evidence_id")
        target_hypothesis = raw.get("target_hypothesis")
        if not isinstance(evidence_id, str) or not isinstance(target_hypothesis, str):
            return None

        matching = [
            (key, record)
            for key, record in allowed.items()
            if key[0] == evidence_id
            and (
                key[1] == target_hypothesis
                or (
                    record.target_type == "decision"
                    and target_hypothesis == "decision-level evidence requirement"
                )
            )
        ]
        if len(matching) != 1:
            return None

        key, record = matching[0]
        if key in seen:
            continue
        seen.add(key)

        priority = raw.get("priority")
        why_missing = raw.get("why_missing")
        decision_impact = raw.get("decision_impact")
        if (
            priority not in {item.value for item in GapPriority}
            or not isinstance(why_missing, str)
            or not why_missing.strip()
            or not isinstance(decision_impact, str)
            or not decision_impact.strip()
        ):
            return None

        gaps.append(
            EvidenceGap(
                gap_id=f"GAP-{record.graph_id}",
                incident_id=record.incident_id,
                decision_id=record.decision_id,
                evidence_id=evidence_id,
                evidence_type="evidence",
                target_hypothesis=target_hypothesis,
                why_missing=why_missing.strip(),
                decision_impact=decision_impact.strip(),
                priority=GapPriority(priority),
            )
        )

    return sorted(gaps, key=lambda gap: gap.gap_id)


def _validated_ranking_explanations(
    ranked: list[RankedEvidence],
    payload: dict[str, Any],
) -> list[RankingExplanation] | None:
    raw_explanations = payload.get("explanations")
    if not isinstance(raw_explanations, list):
        return None

    expected_ids = [item.evidence_id for item in ranked]
    by_id: dict[str, RankingExplanation] = {}
    for raw in raw_explanations:
        if not isinstance(raw, dict):
            return None

        evidence_id = raw.get("evidence_id")
        explanation = raw.get("explanation")
        strengths = raw.get("strengths")
        tradeoffs = raw.get("tradeoffs")
        if (
            not isinstance(evidence_id, str)
            or evidence_id not in expected_ids
            or not isinstance(explanation, str)
            or not explanation.strip()
            or not isinstance(strengths, list)
            or not all(isinstance(item, str) for item in strengths)
            or not isinstance(tradeoffs, list)
            or not all(isinstance(item, str) for item in tradeoffs)
        ):
            return None

        by_id[evidence_id] = RankingExplanation(
            evidence_id=evidence_id,
            explanation=explanation.strip(),
            strengths=tuple(item.strip() for item in strengths if item.strip()),
            tradeoffs=tuple(item.strip() for item in tradeoffs if item.strip()),
        )

    if set(by_id) != set(expected_ids):
        return None

    return [by_id[evidence_id] for evidence_id in expected_ids]
