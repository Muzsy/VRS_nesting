# Orbit Exact Next-Event Specification (Normative)

File: `docs/nesting_engine/orbit_next_event_spec.md`

Scope: concave `ExactOrbit` branch in `rust/nesting_engine/src/nfp/concave.rs`.

This document defines the required, deterministic next-event behavior for orbit sliding, and the trace fields used by golden trace checks.

## 1. Definitions

1. `A`: fixed polygon ring (CCW, simple).
2. `B`: moving polygon ring (CCW, simple), translated by `p`.
3. `touching_group`: deterministically ordered contact set produced by edge-edge touching/intersection checks.
4. `candidate_direction`: normalized integer slide vector derived from touching contacts.
5. `event`: first valid contact transition reached by sliding with `p + v * t`, where `t > 0` is a reduced fraction.

## 2. Event Types

`next_event_kind` must be one of:

1. `vertex_b_to_edge_a`
2. `vertex_a_to_edge_b`

Event candidate payload:

1. `t = num / den`, reduced by gcd, `den > 0`, `num > 0`
2. `vertex_idx`
3. `edge_idx`
4. `event_kind`

## 3. Touching Group Rules

1. Raw contacts are collected from touching/intersecting edge pairs `(edge_a, edge_b, point)`.
2. Contacts are sorted deterministically by `(edge_a, edge_b, point.x, point.y)`.
3. Contacts are deduplicated.
4. If multiple contacts exist, connectivity components are built with shared `edge_a`, shared `edge_b`, or identical `point`.
5. The selected touching component is the one with:
   1. largest size first,
   2. then smallest deterministic component key.

This implements touching-group-first orbit decisions in the Burke + Luo/Rao spirit, but pinned to the current integer implementation.

## 4. Next-Event Selection

Given current translation `p` and a sorted touching group:

1. Build deterministic candidate directions from contact edges.
2. Sort candidate directions by:
   1. quadrant
   2. cross-product angular order
   3. lexicographic vector `(dx, dy)`
   4. source metadata `(source_kind, source_edge_a, source_edge_b)`
3. For each candidate direction in sorted order:
   1. enumerate event candidates from both `vertex(B)->edge(A)` and `vertex(A)->edge(B)` families,
   2. keep only positive `t`,
   3. require projected contact to lie on edge segment,
   4. require no strict overlap at `p + v * t`,
   5. choose the smallest positive `t`,
   6. tie-break by `(event_kind, vertex_idx, edge_idx, next_translation.x, next_translation.y)`.
4. Reject zero movement and immediate backtracking to previous translation.
5. First surviving candidate direction is the chosen next step.

## 5. Invariants

1. No penetration:
   strict overlap is forbidden at accepted event translation.
2. Monotonicity:
   accepted event must satisfy `t > 0`.
3. Contact-set stability:
   touching signature for a step is deterministic from sorted touching contacts.
4. Loop handling:
   visited state hash is over `(translation, touching_group)`; repeated signature means loop.
5. Dead-end handling:
   if no valid next step exists, outcome is explicit dead-end.
6. Max-step handling:
   exceeding `max_steps` yields explicit max-step outcome.
7. Fallback policy:
   only `enable_fallback=true` can return stable concave fallback; otherwise explicit orbit error.

## 6. Trace Format (Golden Check)

The trace format is deterministic and minimal. For each captured step:

1. `step_index` (0-based)
2. `touching_group_signature` (deterministic string from sorted contacts)
3. `chosen_direction`:
   1. `dx`
   2. `dy`
4. `next_event_kind`
5. `next_event_t_num`
6. `next_event_t_den`
7. `tie_break_reason` (deterministic ordering key summary)

Example shape (JSON):

```json
{
  "step_index": 0,
  "touching_group_signature": "a0:b0@-3,0|a0:b1@0,0",
  "chosen_direction": {"dx": 1, "dy": 0},
  "next_event_kind": "vertex_b_to_edge_a",
  "next_event_t_num": 11,
  "next_event_t_den": 1,
  "tie_break_reason": "dir[q0|1,0|src0|a0|b0];event[vertex_b_to_edge_a|v0|e1]"
}
```

Golden trace smoke checks must validate at least the first 1-3 steps byte-identically on these fields.
