# RAG Layers Setup (CodeGraph + Artifacts)

## 1) Code Graph RAG

Baseline commands in repo root:

```bash
scripts/codegraph/rebuild_and_gate.sh prod
```

Switch back to full indexing:

```bash
scripts/codegraph/rebuild_and_gate.sh full
~/.local/bin/cgc watch .
```

Run standard query pack:

```bash
scripts/codegraph/query_playbook.sh
```

Run and save benchmark smoke output:

```bash
scripts/codegraph/eval_rag_smoke.sh
```

Run only gates without index rebuild:

```bash
SKIP_INDEX=true scripts/codegraph/rebuild_and_gate.sh prod
```

## 2) Artifact RAG

Keep artifact corpus separated from code graph ranking.

Primary artifact paths:
- `codex-hermes-loop/runs/`
- `codex-hermes-loop/artifacts/`
- `codex/reports/`
- `*.md` under repo root
- benchmark and deep-research reports

Recommended pattern:
- expose artifact retrieval via a separate MCP tool endpoint
- use metadata filters (`source=hermes|report|benchmark|decision`)
- do not merge artifact ranking with code symbol/callgraph ranking

## 3) Quality Gates (Repeatable)

Use these 4 canonical checks after each index/config change:
1. call chain around `can_place`
2. `cavity_prepack` expansion locations
3. NFP placement strategy defining files
4. BLF fallback code paths

Evidence should be stored in:
- `codex-hermes-loop/evals/codegraph_eval_*.log`

## 4) Notes

- Neo4j is required for best compatibility with inherit/vector resolve.
- `ENABLE_VECTOR_RESOLVE=true` is optional and slower; enable only if ambiguity remains high after inherit resolve.
