# JSON canonicalization for `determinism_hash`

> **File:** `docs/nesting_engine/json_canonicalization.md`
>
> **Purpose:** Define the repository-native, cross-language contract used to compute `meta.determinism_hash`.
>
> **Status:** **Normative** (must match code behavior).

---

## 1. Scope

This document defines the canonicalization contract used inside this repository between:

- Rust output builder: `rust/nesting_engine/src/export/output_v2.rs`
- Python verifier/canonicalizer: `scripts/canonicalize_json.py`

This is a **repo-native contract**, not a general-purpose RFC 8785/JCS implementation requirement.

---

## 2. Hash definition

`meta.determinism_hash` is defined as:

```text
determinism_hash = "sha256:" + SHA-256( UTF8( canonical_hash_view_v1_json ) )
```

Where `canonical_hash_view_v1_json` is generated from the derived hash-view schema
`nesting_engine.hash_view.v1` described below.

---

## 3. Hash-view schema (`nesting_engine.hash_view.v1`)

The hash-view MUST be a JSON object with exactly these top-level keys:

- `placements`
- `schema_version`

`schema_version` MUST be exactly:

```text
nesting_engine.hash_view.v1
```

Each `placements[]` entry MUST contain exactly:

- `part_id` (string)
- `rotation_deg` (integer)
- `sheet_id` (string)
- `x_scaled_i64` (integer)
- `y_scaled_i64` (integer)

No additional hash-view keys are part of the v1 contract.

---

## 4. Derivation and ordering rules

### 4.1 Coordinate scaling

`x_scaled_i64` and `y_scaled_i64` are derived from output `x_mm`/`y_mm` values using:

- `SCALE = 1_000_000`
- round-half-away-from-zero

So:

- `x_scaled_i64 = round_half_away_from_zero(x_mm * SCALE)`
- `y_scaled_i64 = round_half_away_from_zero(y_mm * SCALE)`

### 4.2 Placement ordering

Before serialization, `placements` MUST be sorted ascending by:

1. `sheet_id`
2. `part_id`
3. `rotation_deg`
4. `x_scaled_i64`
5. `y_scaled_i64`

---

## 5. Canonical JSON byte form

The canonical JSON byte form for hashing is:

- compact JSON (no insignificant whitespace),
- UTF-8 encoded,
- object keys sorted lexicographically.

Repository reference implementations:

- Python: `json.dumps(..., ensure_ascii=False, sort_keys=True, separators=(",", ":"))`
- Rust: `BTreeMap` key ordering + `serde_json::to_string(...)`

Important:

- The contract target is **Rust <-> Python equivalence inside this repo**.
- The contract does **not** claim full RFC 8785/JCS compatibility beyond the above rules.

---

## 6. Determinism evidence in gate

- Unit evidence: `determinism_` tests in `rust/nesting_engine/src/export/output_v2.rs`
- Smoke evidence: `scripts/smoke_nesting_engine_determinism.sh`
  - compares full `nest` stdout JSON bytes across runs,
  - recomputes canonical hash in Python,
  - checks equality against solver `meta.determinism_hash`.

---

## 7. Versioning policy

`schema_version` must remain `nesting_engine.hash_view.v1` unless canonical bytes actually change.

A version bump is required if any of the following changes:

- hash-view field set,
- sort key tuple,
- scaling constant or rounding behavior,
- canonical JSON serialization rule.

---

## 8. References

- `docs/nesting_engine/io_contract_v2.md`
- `docs/nesting_engine/tolerance_policy.md`
- `rust/nesting_engine/src/export/output_v2.rs`
- `scripts/canonicalize_json.py`
