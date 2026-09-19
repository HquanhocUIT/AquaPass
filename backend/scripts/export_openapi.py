"""Export the live FastAPI contract to a versioned OpenAPI JSON file."""

import json
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app  # noqa: E402


def main() -> None:
    destination = REPOSITORY_ROOT / "docs" / "api" / "openapi.json"
    destination.write_text(
        json.dumps(app.openapi(), indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"OpenAPI exported to {destination}")


if __name__ == "__main__":
    main()
