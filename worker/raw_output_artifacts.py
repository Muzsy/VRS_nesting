from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class RawArtifactSpec:
    filename: str
    artifact_kind: str
    legacy_artifact_type: str


@dataclass(frozen=True)
class PersistedRawArtifact:
    filename: str
    artifact_kind: str
    storage_path: str
    content_sha256: str
    size_bytes: int


UploadFn = Callable[..., None]
RegisterFn = Callable[..., None]


_RAW_ARTIFACT_SPECS: tuple[RawArtifactSpec, ...] = (
    RawArtifactSpec(filename="solver_stdout.log", artifact_kind="log", legacy_artifact_type="solver_stdout"),
    RawArtifactSpec(filename="solver_stderr.log", artifact_kind="log", legacy_artifact_type="solver_stderr"),
    RawArtifactSpec(filename="solver_output.json", artifact_kind="solver_output", legacy_artifact_type="solver_output"),
    RawArtifactSpec(filename="runner_meta.json", artifact_kind="log", legacy_artifact_type="runner_meta"),
    RawArtifactSpec(filename="run.log", artifact_kind="log", legacy_artifact_type="run_log"),
)


def _require_id(value: str, *, field: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        raise RuntimeError(f"invalid {field}")
    return cleaned


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _metadata_json(*, spec: RawArtifactSpec, size_bytes: int, content_sha256: str) -> dict[str, Any]:
    return {
        "legacy_artifact_type": spec.legacy_artifact_type,
        "raw_output_scope": "h1_e5_t3",
        "filename": spec.filename,
        "size_bytes": int(size_bytes),
        "content_sha256": content_sha256,
    }


def canonical_raw_output_storage_path(
    *,
    project_id: str,
    run_id: str,
    artifact_kind: str,
    content_sha256: str,
    extension: str,
) -> str:
    project = _require_id(project_id, field="project_id")
    run = _require_id(run_id, field="run_id")
    kind = _require_id(artifact_kind, field="artifact_kind")
    digest = _require_id(content_sha256, field="content_sha256")
    ext = _require_id(extension, field="extension").lower().lstrip(".")
    return f"projects/{project}/runs/{run}/{kind}/{digest}.{ext}"


def persist_raw_output_artifacts(
    *,
    run_dir: Path,
    project_id: str,
    run_id: str,
    storage_bucket: str,
    upload_object: UploadFn,
    register_artifact: RegisterFn,
) -> list[PersistedRawArtifact]:
    _require_id(storage_bucket, field="storage_bucket")
    if not run_dir.is_dir():
        return []

    persisted: list[PersistedRawArtifact] = []
    for spec in _RAW_ARTIFACT_SPECS:
        path = run_dir / spec.filename
        if not path.is_file():
            continue

        payload = path.read_bytes()
        content_sha256 = _sha256_bytes(payload)
        suffix = path.suffix.lower().lstrip(".") or "bin"
        storage_path = canonical_raw_output_storage_path(
            project_id=project_id,
            run_id=run_id,
            artifact_kind=spec.artifact_kind,
            content_sha256=content_sha256,
            extension=suffix,
        )
        metadata = _metadata_json(spec=spec, size_bytes=len(payload), content_sha256=content_sha256)

        upload_object(bucket=storage_bucket, object_key=storage_path, payload=payload)
        register_artifact(
            run_id=run_id,
            artifact_kind=spec.artifact_kind,
            storage_bucket=storage_bucket,
            storage_path=storage_path,
            metadata_json=metadata,
        )

        persisted.append(
            PersistedRawArtifact(
                filename=spec.filename,
                artifact_kind=spec.artifact_kind,
                storage_path=storage_path,
                content_sha256=content_sha256,
                size_bytes=len(payload),
            )
        )

    persisted.sort(key=lambda item: item.storage_path)
    return persisted


def persisted_raw_artifacts_json(records: list[PersistedRawArtifact]) -> str:
    payload = [
        {
            "filename": item.filename,
            "artifact_kind": item.artifact_kind,
            "storage_path": item.storage_path,
            "content_sha256": item.content_sha256,
            "size_bytes": item.size_bytes,
        }
        for item in records
    ]
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
