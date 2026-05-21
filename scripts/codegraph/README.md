# CodeGraph + Artifact RAG Gate

## Architecture

Two-layer RAG setup:

1. Code Graph RAG
- Source: `VRS_nesting` repository code
- Engine: CodeGraphContext (`cgc`) on Neo4j
- Purpose: symbols, callers/callees, call chains, dependency/architecture relationships

2. Artifact RAG
- Source: reports/logs/benchmarks/eval outputs
- Current implementation: `artifact_rag_v0_rg` (deterministic `rg` over artifact dirs)
- Purpose: benchmark evidence, run logs, report history, decision artifacts

## Routing Rule

- code question -> CodeGraphContext MCP
- report/log/benchmark question -> Artifact RAG
- uncertain/mixed question -> both, with separately labeled evidence

When both are used, keep sections separate:
- Code Graph Evidence
- Artifact Evidence
- Conclusion
- Confidence / gaps

## Commands

One-command rebuild + quality gate:

```bash
scripts/codegraph/rebuild_and_gate.sh prod
```

Quick gate without rebuilding index:

```bash
SKIP_INDEX=true scripts/codegraph/rebuild_and_gate.sh prod
```

Health check:

```bash
scripts/codegraph/health_check.sh
```

Eval smoke (golden query set):

```bash
scripts/codegraph/eval_rag_smoke.sh
```

Artifact RAG v0 direct query:

```bash
scripts/codegraph/artifact_rag_v0_rg.sh "lv8|benchmark|placements=276"
```

## Logs

All quality-gate logs are written under:

- `/home/muszy/codex-hermes-loop/evals/`

Eval naming:

- `YYYYMMDD_HHMM_rag_smoke.log`

## PASS/FAIL Interpretation

- `PASS`: expected evidence was found for the target layer.
- `FAIL`: required evidence missing, command failed, or config/runtime mismatch.
- `eval_rag_smoke.sh` exits non-zero if any critical query fails.

## Known Caveat

CodeGraphContext can print misleading context text such as `Database: falkordb`.
Treat actual query evidence and runtime `--database neo4j` results as authoritative.
