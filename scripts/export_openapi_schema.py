#!/usr/bin/env python3
"""Export FastAPI OpenAPI schema to a static JSON artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.main import app  # noqa: E402


def main() -> int:
    output_path = ROOT / "docs" / "api_openapi_schema.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    schema = app.openapi()
    output_path.write_text(json.dumps(schema, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] OpenAPI schema exported: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
