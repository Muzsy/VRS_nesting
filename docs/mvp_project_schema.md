# MVP project schema

## Purpose
This document defines the minimal project JSON contract for the first table-solver CLI flow.

## Version
- Current schema version: `v1`

## Required top-level fields
- `version` (string): must be `v1`
- `name` (string): non-empty project name
- `seed` (integer): deterministic seed, `>= 0`
- `time_limit_s` (integer): solver time budget in seconds, `> 0`
- `stocks` (array): non-empty list of stock definitions
- `parts` (array): non-empty list of part definitions

Unknown top-level fields are rejected.

## Stock item schema
Each stock item is an object with required fields:
- `id` (string): unique stock id
- `width` (number): width in model units, `> 0`
- `height` (number): height in model units, `> 0`
- `quantity` (integer): available count, `> 0`

Unknown stock fields are rejected.

## Part item schema
Each part item is an object with required fields:
- `id` (string): unique part id
- `width` (number): width in model units, `> 0`
- `height` (number): height in model units, `> 0`
- `quantity` (integer): demand count, `> 0`

Optional part fields:
- `allowed_rotations_deg` (array of integer degrees, default: `[0]`)
  - allowed values: `0`, `90`, `180`, `270`
  - duplicates are normalized out

Unknown part fields are rejected.

## Notes
- This is an MVP schema for deterministic bootstrap flow.
- Geometry references, nesting options, and export config are out of scope for this version.
