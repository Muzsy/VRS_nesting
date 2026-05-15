# ADR-0001 — BLF is not a production quality solver for LV8 nesting

## Status

Accepted (2026-05-12)

## Decision

BLF (Bottom-Left-Fill) must not be used as the main quality solver for LV8 /
industrial irregular nesting.

## Allowed use

BLF may only be used for:

- diagnostics
- fallback comparison
- smoke tests
- minimal baselines / reproductions
- debugging `can_place` / narrow-phase problems

## Required quality paths

Quality-targeted work must focus on:

- NFP / CFR-based placement
- `cavity_prepack` / `quality_cavity_prepack` profile
- post-placement compaction
- multi-start / SA quality search

## Rationale

The LV8 two-sheet target requires dense irregular placement with internal
contours (holes) and 10 mm clearance. Prior Hermes-driven benchmark runs
(see `codex/reports/nesting_engine/lv8_2sheet_10mm_600s_quality_search_20260511.md`)
showed that the BLF path:

1. Is not a credible quality path for LV8 — best result was 12 placed types
   on 1 sheet at ~17% utilization, never reaching the 276/276 instance target
   on 2 sheets.
2. Degenerates catastrophically on LV8 concave-polygon combinations starting
   from just two part types (e.g., `LV8_00035` + `LV8_00057`), producing
   30 s+ runtimes / apparent infinite loops independent of hole presence.

Additionally, the engine currently falls back from `--placer nfp` to BLF
whenever the input has holes (see `main.rs` "hybrid gating"), unless
`--nfp-kernel cgal_reference` is set. This makes NFP without prepack
ineffective for the LV8 case; the workable non-BLF quality paths are
therefore:

- `quality_cavity_prepack` (NFP + SA + slide, with `part_in_part=prepack`
  removing holes from the engine input upstream)
- `quality_cavity_prepack_cgal_reference` (same but CGAL kernel, dev-only)

## Implications

- Benchmark harnesses that target LV8 quality must default to one of the
  cavity-prepack profiles.
- Any new "fast" BLF path may exist, but must not be presented as a quality
  baseline for industrial irregular inputs.
- A run that places only `12/12 types` is never sufficient evidence of a
  pass — the unit of success is `276/276 instances` on ≤ 2 sheets, validated.
