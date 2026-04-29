#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.routes.runs import _create_signed_download_for_artifact
from api.supabase_client import SupabaseHTTPError


@dataclass
class _SettingsStub:
    storage_bucket: str = "source-files"
    signed_url_ttl_s: int = 900


class _FakeSupabase:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def create_signed_download_url(
        self,
        *,
        access_token: str,
        bucket: str,
        object_key: str,
        expires_in: int,
    ) -> dict[str, str]:
        self.calls.append(f"{bucket}:{object_key}")
        if bucket == "run-artifacts":
            raise SupabaseHTTPError("simulated sign failure")
        return {
            "download_url": f"https://example.test/{bucket}/{object_key}",
            "expires_at": "2026-04-29T00:00:00+00:00",
        }


def main() -> int:
    settings = _SettingsStub()
    supabase = _FakeSupabase()

    signed = _create_signed_download_for_artifact(
        supabase=supabase,
        access_token="token",
        artifact={
            "storage_bucket": "run-artifacts",
            "storage_key": "runs/39e66711-f6eb-471c-8e1f-200d6da91014/inputs/solver_input_snapshot.json",
        },
        settings=settings,
    )
    assert signed["download_url"].startswith("https://example.test/source-files/")
    assert len(supabase.calls) == 2
    print("PASS smoke_cavity_t0_artifact_recovery_and_baseline_replay")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
