from __future__ import annotations

import json
import re
from typing import Any

import httpx


class GeminiError(RuntimeError):
    """Raised when Gemini cannot return a valid structured response."""


class GeminiClient:
    """Small REST client for Gemini structured JSON generation.

    The client deliberately uses the REST API instead of adding another SDK
    dependency. It sends the API key in the ``x-goog-api-key`` header and
    never includes it in errors or logs.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float = 12.0,
    ) -> None:
        if not api_key.strip():
            raise GeminiError("Gemini API key is not configured")
        if not model.strip():
            raise GeminiError("Gemini model is not configured")

        self._api_key = api_key.strip()
        self.model = model.strip()
        self.timeout_seconds = timeout_seconds

    def generate_json(
        self,
        *,
        prompt: str,
        response_schema: dict[str, Any],
    ) -> dict[str, Any]:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "responseFormat": {
                    "text": {
                        "mimeType": "application/json",
                        "schema": response_schema,
                    }
                },
            },
        }

        try:
            response = httpx.post(
                url,
                headers={
                    "x-goog-api-key": self._api_key,
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise GeminiError("Gemini request failed") from exc

        try:
            text = body["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise GeminiError("Gemini response did not contain text") from exc

        return _parse_json_object(text)


def _parse_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
    if fenced:
        cleaned = fenced.group(1).strip()

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise GeminiError("Gemini returned invalid JSON") from exc

    if not isinstance(payload, dict):
        raise GeminiError("Gemini JSON response must be an object")

    return payload
