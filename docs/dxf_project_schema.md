# DXF Project Schema

## Purpose
This document defines the strict project JSON contract for the real DXF + Sparrow flow.

## Version
- Current DXF schema version: `dxf_v1`

## Required top-level fields
- `version` (string): must be `dxf_v1`
- `name` (string): non-empty project name
- `seed` (integer): deterministic seed, `>= 0`
- `time_limit_s` (integer): Sparrow time budget in seconds, `> 0`
- `units` (string): geometry units label (for MVP expected `mm`)
- `spacing_mm` (number): minimum part-to-part spacing, `>= 0`
- `margin_mm` (number): minimum part-to-stock edge margin, `>= 0`
- `stocks_dxf` (array): non-empty list of stock geometry references
- `parts_dxf` (array): non-empty list of part geometry references

Unknown top-level fields are rejected.

## `stocks_dxf` / `parts_dxf` item schema
Each item is an object with required fields:
- `id` (string): unique logical id
- `path` (string): path to source geometry file (`.json` fixture or `.dxf`)
- `quantity` (integer): count, `> 0`

Optional item fields:
- `allowed_rotations_deg` (array of integer degrees, default: `[0]`)
  - allowed values: `0`, `90`, `180`, `270`
  - duplicates are normalized out

Unknown item fields are rejected.

## Notes
- `version=v1` remains the table-solver schema and is validated separately.
- `dxf_v1` is intentionally isolated to prevent schema mixing between flows.
