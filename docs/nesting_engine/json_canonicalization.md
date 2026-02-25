# JSON canonicalization for determinism

> **File:** `docs/nesting_engine/json_canonicalization.md`
>
> **Purpose:** Define a single, unambiguous, cross-language method to compute `determinism_hash` for solver outputs.
>
> **Status:** **Normative** (must be followed exactly).

---

## 1. Scope

This document specifies:

* The **canonical byte representation** used to compute `determinism_hash`.
* The **hash-view** transformation that removes floating-point serialization variance.
* The **stable ordering rules** required for deterministic outputs.

It does **not** specify:

* The solver algorithm.
* The full I/O schema (see `docs/nesting_engine/solver_io_contract_v2.md`).

---

## 2. Design choice

### 2.1 Base canonicalization: JCS-compatible subset for `hash_view_v1`

The project targets a **JCS-compatible subset** for `hash_view_v1` instead of requiring a full RFC 8785 serializer implementation.

For this hash-view, determinism is guaranteed by these normative constraints:

* Object member (key) ordering is lexicographic.
* Serialization contains no insignificant whitespace.
* Encoding is UTF-8.
* Numbers in hash-view are integers only.
* Strings follow standard JSON escaping rules.

This is sufficient for byte-identical canonicalization across the Rust and Python reference implementations used in this repository.

### 2.2 Numeric stability: hash-view with scaled integers

JSON numbers and floating-point formatting are a common cross-language nondeterminism source.

To avoid this, `determinism_hash` is computed **not** from the raw output JSON, but from a derived **hash-view** where all placement coordinates are represented as **scaled integers**.

This aligns with the project-wide scale policy (`SCALE = 1_000_000`, see `docs/nesting_engine/tolerance_policy.md`).

---

## 3. Terminology

* **Raw output**: the human- and tool-facing solver output JSON (may contain `*_mm` floating-point numbers).
* **Hash-view**: a derived JSON object containing only fields needed for determinism hashing, with numeric fields converted to scaled integers.
* **Canonical JSON (JCS-subset)**: the project-defined, JCS-compatible subset serialization rules from Section 6.

---

## 4. Hash definition

`determinism_hash` is defined as:

```
determinism_hash = SHA-256( UTF8( canonical_hash_view_v1_json ) )
```

Where:

* `hash_view_json` is the hash-view object as defined in Section 5.
* `canonical_hash_view_v1_json` is the canonical byte representation produced by the rules in Section 6.
* `UTF8(...)` converts the canonical JSON text to bytes (UTF-8).
* `SHA-256(...)` returns a lowercase hex string (64 hex chars).

---

## 5. Hash-view specification

### 5.1 Allowed fields

The hash-view **MUST** be a JSON object with exactly these top-level keys:

* `schema_version`
* `placements`

No additional top-level keys are allowed.

#### 5.1.1 `schema_version`

* Type: string
* Value: **must** be exactly: `"nesting_engine.hash_view.v1"`

#### 5.1.2 `placements`

* Type: array
* Content: placement entries (Section 5.2)

### 5.2 Placement entry

Each placement entry **MUST** be a JSON object with exactly these keys:

* `sheet_id` (string)
* `part_id` (string)
* `rotation_deg` (integer)
* `x_scaled_i64` (integer)
* `y_scaled_i64` (integer)

No additional keys are allowed.

### 5.3 Coordinate scaling

`x_scaled_i64` and `y_scaled_i64` are computed from raw output fields `x_mm` and `y_mm` as:

* `x_scaled_i64 = round(x_mm * SCALE)`
* `y_scaled_i64 = round(y_mm * SCALE)`

Where:

* `SCALE` is **exactly** `1_000_000`.
* `round(...)` is **round half away from zero** (i.e., 0.5 rounds to 1, -0.5 rounds to -1).

**Important:** the rounding rule is part of the contract. Implementations must not rely on language defaults if they differ.

### 5.4 Stable ordering of placements

Before canonicalization, the `placements` array **MUST** be sorted in ascending order by the following lexicographic tuple:

1. `sheet_id` (string)
2. `part_id` (string)
3. `rotation_deg` (integer)
4. `x_scaled_i64` (integer)
5. `y_scaled_i64` (integer)

Sorting is stable but stability is irrelevant once keys are unique.

This rule ensures that internal iteration order (hash maps, parallel runs, solver heuristics) does not affect the canonical output.

---

## 6. Canonical JSON requirements for `hash_view_v1`

For `hash_view_v1`, canonical JSON **MUST** satisfy all of the following:

* **Lexicographic key ordering:** object members are serialized in key-sorted order.
* **Whitespace-free JSON:** no insignificant whitespace is allowed.
* **UTF-8 bytes:** hashing input is UTF-8 encoded JSON text.
* **Integer-only numbers:** hash-view numeric fields are integers (`rotation_deg`, `x_scaled_i64`, `y_scaled_i64`).
* **JSON string escaping:** strings are serialized with standard JSON escaping.

The repository reference implementations are normative:

* **Python:** `json.dumps(hash_view, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`
* **Rust:** `BTreeMap`-based key ordering + `serde_json::to_string(...)`

Because the hash-view uses integers only, floating-point rendering variance is excluded by design.

---

## 7. Example

### 7.1 Raw output placements (illustrative)

```json
{
  "placements": [
    {"sheet_id":"S1","part_id":"P2","rotation_deg":90,"x_mm":10.5,"y_mm":20.0},
    {"sheet_id":"S1","part_id":"P1","rotation_deg":0,"x_mm":0.0,"y_mm":0.0}
  ]
}
```

### 7.2 Hash-view (before sorting)

Assuming `SCALE = 1_000_000`:

* `10.5 mm -> 10500000`
* `20.0 mm -> 20000000`

```json
{
  "schema_version":"nesting_engine.hash_view.v1",
  "placements":[
    {"sheet_id":"S1","part_id":"P2","rotation_deg":90,"x_scaled_i64":10500000,"y_scaled_i64":20000000},
    {"sheet_id":"S1","part_id":"P1","rotation_deg":0,"x_scaled_i64":0,"y_scaled_i64":0}
  ]
}
```

### 7.3 Hash-view (after required sorting)

```json
{
  "schema_version":"nesting_engine.hash_view.v1",
  "placements":[
    {"sheet_id":"S1","part_id":"P1","rotation_deg":0,"x_scaled_i64":0,"y_scaled_i64":0},
    {"sheet_id":"S1","part_id":"P2","rotation_deg":90,"x_scaled_i64":10500000,"y_scaled_i64":20000000}
  ]
}
```

### 7.4 Canonical JSON form

Whitespace-free, key-sorted canonical JSON text:

```json
{"placements":[{"part_id":"P1","rotation_deg":0,"sheet_id":"S1","x_scaled_i64":0,"y_scaled_i64":0},{"part_id":"P2","rotation_deg":90,"sheet_id":"S1","x_scaled_i64":10500000,"y_scaled_i64":20000000}],"schema_version":"nesting_engine.hash_view.v1"}
```

`determinism_hash` is the SHA-256 of the UTF-8 bytes of the above string.

---

## 8. Implementation notes (non-normative)

* **Do not** hash pretty-printed raw output JSON.
* **Do not** hash language-native objects directly.
* Always build the **hash-view**, sort placements, produce canonical bytes with Section 6 rules, then hash.

Reference implementation anchors in this repo:

* Rust: `rust/nesting_engine/src/export/output_v2.rs`
* Python: `scripts/canonicalize_json.py`

---

## 9. Versioning

Changes to any of the following require a new `schema_version` value:

* Placement sort key
* Scaling factor `SCALE`
* Rounding rule
* Allowed fields in the hash-view
* Any RFC 8785 compliance deviations

---

## 10. References

* RFC 8785 — JSON Canonicalization Scheme (JCS)
* `docs/nesting_engine/tolerance_policy.md` (SCALE policy)
* `docs/nesting_engine/solver_io_contract_v2.md` (I/O schema)
