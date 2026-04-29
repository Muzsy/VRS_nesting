from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from api.routes.runs import _artifact_url_bucket_candidates, _create_signed_download_for_artifact
from api.supabase_client import SupabaseHTTPError


@dataclass
class _SettingsStub:
    storage_bucket: str = "source-files"
    signed_url_ttl_s: int = 900


class _FakeSupabase:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def create_signed_download_url(
        self,
        *,
        access_token: str,
        bucket: str,
        object_key: str,
        expires_in: int,
    ) -> dict[str, Any]:
        self.calls.append((bucket, object_key))
        if bucket == "run-artifacts":
            raise SupabaseHTTPError("signed download failed for run-artifacts")
        return {
            "download_url": f"https://example.test/{bucket}/{object_key}",
            "expires_at": "2026-04-29T00:00:00+00:00",
        }


def test_artifact_url_bucket_candidates_dedup_and_order() -> None:
    settings = _SettingsStub(storage_bucket="source-files")
    artifact = {
        "storage_bucket": "run-artifacts",
        "storage_key": "runs/abc/inputs/solver_input_snapshot.json",
    }
    buckets = _artifact_url_bucket_candidates(artifact=artifact, settings=settings)
    assert buckets == ["run-artifacts", "source-files"]


def test_create_signed_download_for_artifact_falls_back_to_settings_bucket() -> None:
    settings = _SettingsStub(storage_bucket="source-files")
    artifact = {
        "storage_bucket": "run-artifacts",
        "storage_key": "runs/abc/inputs/solver_input_snapshot.json",
    }
    supabase = _FakeSupabase()

    signed = _create_signed_download_for_artifact(
        supabase=supabase,
        access_token="token",
        artifact=artifact,
        settings=settings,
    )

    assert signed["download_url"] == "https://example.test/source-files/runs/abc/inputs/solver_input_snapshot.json"
    assert supabase.calls == [
        ("run-artifacts", "runs/abc/inputs/solver_input_snapshot.json"),
        ("source-files", "runs/abc/inputs/solver_input_snapshot.json"),
    ]


def test_create_signed_download_for_artifact_raises_when_storage_key_missing() -> None:
    settings = _SettingsStub(storage_bucket="source-files")
    artifact = {
        "storage_bucket": "run-artifacts",
        "storage_key": "",
    }
    supabase = _FakeSupabase()

    with pytest.raises(SupabaseHTTPError, match="storage_key is empty"):
        _create_signed_download_for_artifact(
            supabase=supabase,
            access_token="token",
            artifact=artifact,
            settings=settings,
        )
