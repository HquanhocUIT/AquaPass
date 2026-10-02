from __future__ import annotations

from dataclasses import dataclass

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app
from app.modules.ai.grounded_insights import (
    suggest_evidence_gaps,
    explain_ranking,
)
from app.modules.ai.gemini_client import GeminiClient
from app.modules.evidence.gap_detector import EvidenceGraphRecord
from app.modules.ranking.ranking_engine import EvidenceCandidate


client = TestClient(app)


@dataclass
class FakeGeminiClient:
    response: dict

    def generate_json(self, *, prompt: str, response_schema: dict) -> dict:
        assert prompt
        assert response_schema["type"] == "object"
        return self.response


def _settings() -> Settings:
    return Settings(
        llm_enabled=True,
        llm_api_key="test-key",
        llm_model="gemini-test",
    )


def _record() -> EvidenceGraphRecord:
    return EvidenceGraphRecord(
        graph_id="G-001",
        incident_id="INC-FISH-001",
        decision_id="DEC-FISH-001",
        source_node="EV-005",
        source_type="evidence",
        relationship="missing_for",
        target_node="HYP-LOW-DO",
        target_type="hypothesis",
        confidence=0.90,
        state="missing",
        rationale="Direct DO measurement is needed for the low-DO hypothesis.",
    )


def _candidate() -> EvidenceCandidate:
    return EvidenceCandidate(
        evidence_id="EV-005",
        candidate_name="Field dissolved oxygen measurement",
        decision_value=0.95,
        reliability=0.90,
        feasibility=0.90,
        cost=0.20,
        time=0.20,
    )


def test_gemini_client_uses_structured_json_request(monkeypatch) -> None:
    captured: dict = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "candidates": [
                    {"content": {"parts": [{"text": '{"ok": true}'}]}}
                ]
            }

    def fake_post(url, *, headers, json, timeout):
        captured.update({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr("httpx.post", fake_post)

    result = GeminiClient(
        api_key="test-key",
        model="gemini-test",
    ).generate_json(
        prompt="Return JSON.",
        response_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}},
    )

    assert result == {"ok": True}
    assert captured["headers"]["x-goog-api-key"] == "test-key"
    assert captured["json"]["generationConfig"]["responseFormat"]["text"]["mimeType"] == "application/json"


def test_gap_suggestions_use_deterministic_fallback_when_ai_disabled() -> None:
    result = suggest_evidence_gaps(
        [_record()],
        app_settings=Settings(llm_enabled=False),
    )

    assert result.metadata.provider == "deterministic_fallback"
    assert len(result.gaps) == 1
    assert result.gaps[0].evidence_id == "EV-005"


def test_gap_suggestions_accept_only_grounded_gemini_ids() -> None:
    result = suggest_evidence_gaps(
        [_record()],
        app_settings=_settings(),
        client=FakeGeminiClient(
            {
                "gaps": [
                    {
                        "evidence_id": "EV-005",
                        "target_hypothesis": "HYP-LOW-DO",
                        "why_missing": "The graph marks the DO measurement as missing.",
                        "decision_impact": "It can distinguish the low-DO explanation.",
                        "priority": "high",
                    }
                ]
            }
        ),
    )

    assert result.metadata.provider == "gemini"
    assert result.gaps[0].why_missing.startswith("The graph")


def test_invalid_gemini_gap_output_falls_back() -> None:
    result = suggest_evidence_gaps(
        [_record()],
        app_settings=_settings(),
        client=FakeGeminiClient(
            {
                "gaps": [
                    {
                        "evidence_id": "INVENTED-ID",
                        "target_hypothesis": "HYP-LOW-DO",
                        "why_missing": "Invented",
                        "decision_impact": "Invented",
                        "priority": "high",
                    }
                ]
            }
        ),
    )

    assert result.metadata.provider == "deterministic_fallback"
    assert result.gaps[0].evidence_id == "EV-005"


def test_ranking_explanations_keep_deterministic_order_and_scores() -> None:
    result = explain_ranking(
        [_candidate()],
        app_settings=_settings(),
        client=FakeGeminiClient(
            {
                "explanations": [
                    {
                        "evidence_id": "EV-005",
                        "explanation": "It leads because decision value and reliability are high.",
                        "strengths": ["high decision value"],
                        "tradeoffs": ["low acquisition burden"],
                    }
                ]
            }
        ),
    )

    assert result.metadata.provider == "gemini"
    assert result.ranked[0].rank == 1
    assert result.explanations[0].evidence_id == "EV-005"
    assert "decision value" in result.explanations[0].explanation


def test_ai_gap_endpoint_returns_fallback_metadata() -> None:
    response = client.post(
        "/api/ai/evidence-gaps",
        json={
            "records": [
                {
                    "graph_id": "G-001",
                    "incident_id": "INC-FISH-001",
                    "decision_id": "DEC-FISH-001",
                    "source_node": "EV-005",
                    "source_type": "evidence",
                    "relationship": "missing_for",
                    "target_node": "HYP-LOW-DO",
                    "target_type": "hypothesis",
                    "confidence": 0.9,
                    "state": "missing",
                    "rationale": "Direct DO measurement is needed.",
                }
            ]
        },
    )

    assert response.status_code == 200
    assert response.json()["provider"] == "deterministic_fallback"
    assert response.json()["gaps"][0]["evidence_id"] == "EV-005"


def test_ai_ranking_endpoint_returns_fallback_explanation() -> None:
    response = client.post(
        "/api/ai/ranking-explanations",
        json={
            "candidates": [
                {
                    "evidence_id": "EV-005",
                    "candidate_name": "Field dissolved oxygen measurement",
                    "decision_value": 0.95,
                    "reliability": 0.90,
                    "feasibility": 0.90,
                    "cost": 0.20,
                    "time": 0.20,
                }
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "deterministic_fallback"
    assert body["results"][0]["evidence_id"] == "EV-005"
    assert body["results"][0]["rank"] == 1
