"""Keep the versioned environment template free of live credentials."""

from pathlib import Path


def test_env_example_contains_only_database_placeholders() -> None:
    example = (Path(__file__).resolve().parents[2] / ".env.example").read_text(
        encoding="utf-8"
    )

    assert "sb_secret_" not in example.lower()
    assert "YOUR_PASSWORD" in example
    assert "PROJECT_REF" in example
    assert "POOLER_HOST" in example
