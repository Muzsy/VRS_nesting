#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
QUERY_FILE="$REPO_ROOT/scripts/codegraph/golden_queries.json"
OUT_DIR="/home/muszy/codex-hermes-loop/evals"
STAMP="$(date +%Y%m%d_%H%M)"
LOG_FILE="$OUT_DIR/${STAMP}_rag_smoke.log"
RAW_DIR="$OUT_DIR/raw_${STAMP}"

mkdir -p "$OUT_DIR" "$RAW_DIR"

if [[ ! -f "$QUERY_FILE" ]]; then
  echo "Missing golden query set: $QUERY_FILE" >&2
  exit 2
fi

python3 - "$REPO_ROOT" "$QUERY_FILE" "$LOG_FILE" "$RAW_DIR" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

repo_root = Path(sys.argv[1])
query_file = Path(sys.argv[2])
log_file = Path(sys.argv[3])
raw_dir = Path(sys.argv[4])

data = json.loads(query_file.read_text())
queries = data["queries"]

sections = {"code_graph": [], "artifact": [], "mixed": []}
summary = {"total": 0, "passed": 0, "failed": 0, "critical_failed": 0}


def run_cmd(cmd: str):
    proc = subprocess.run(
        cmd,
        shell=True,
        cwd=str(repo_root),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return proc.returncode, proc.stdout


def eval_check(check, output: str):
    expected_all = check.get("expected_all", [])
    expected_any = check.get("expected_any", [])
    min_ev = int(check.get("minimum_evidence_required", 1))

    missing_all = [tok for tok in expected_all if tok not in output]
    any_hits = [tok for tok in expected_any if tok in output]

    evidence_hits = len(any_hits) + (len(expected_all) - len(missing_all))
    ok = not missing_all
    if expected_any:
        ok = ok and (len(any_hits) > 0)
    ok = ok and (evidence_hits >= min_ev)

    return {
        "ok": ok,
        "missing_all": missing_all,
        "any_hits": any_hits,
        "evidence_hits": evidence_hits,
    }


def write_block(lines):
    with log_file.open("a") as f:
        f.write("\n".join(lines) + "\n")

# header
write_block([
    "# RAG Smoke Eval",
    f"repo={repo_root}",
    f"query_set={query_file}",
    f"raw_dir={raw_dir}",
    "",
    "Routing rule:",
    "- code question -> CodeGraphContext",
    "- report/log/benchmark query -> artifact_rag_v0_rg",
    "- mixed query -> both, evidence separated",
    "",
])

for q in queries:
    qid = q["id"]
    layer = q["layer"]
    summary["total"] += 1

    q_lines = [
        f"## {qid}",
        f"layer={layer}",
        f"query_text={q['query_text']}",
        f"why={q['why_included']}",
        f"pass_criteria={q['pass_criteria']}",
        f"fail_criteria={q['fail_criteria']}",
        "",
    ]

    check_results = []
    for idx, check in enumerate(q["checks"], start=1):
        cmd = check["command"]
        rc, out = run_cmd(cmd)
        raw_file = raw_dir / f"{qid}_check{idx}.log"
        raw_file.write_text(out)

        ev = eval_check(check, out)
        ok = (rc == 0) and ev["ok"]
        check_results.append((ok, check, ev, raw_file, rc))

    q_ok = all(x[0] for x in check_results)
    if q_ok:
        summary["passed"] += 1
    else:
        summary["failed"] += 1
        if q.get("critical", False):
            summary["critical_failed"] += 1

    if layer == "mixed":
        q_lines.append("Code Graph Evidence")
        for ok, check, ev, raw_file, rc in check_results:
            if check.get("label") == "code_graph":
                q_lines.extend([
                    f"- check={check['label']} status={'PASS' if ok else 'FAIL'} rc={rc}",
                    f"- raw={raw_file}",
                    f"- evidence_hits={ev['evidence_hits']} any_hits={ev['any_hits']}",
                    f"- missing_all={ev['missing_all']}",
                ])
        q_lines.append("")
        q_lines.append("Artifact Evidence")
        for ok, check, ev, raw_file, rc in check_results:
            if check.get("label") == "artifact":
                q_lines.extend([
                    f"- check={check['label']} status={'PASS' if ok else 'FAIL'} rc={rc}",
                    f"- raw={raw_file}",
                    f"- evidence_hits={ev['evidence_hits']} any_hits={ev['any_hits']}",
                    f"- missing_all={ev['missing_all']}",
                ])
        q_lines.append("")
        q_lines.append(f"Conclusion: {'PASS' if q_ok else 'FAIL'}")
        q_lines.append(
            "Confidence / gaps: "
            + ("high confidence (both layers yielded expected evidence)" if q_ok else "gap in at least one layer; inspect raw logs")
        )
    else:
        for ok, check, ev, raw_file, rc in check_results:
            q_lines.extend([
                f"- check={check.get('label','n/a')} status={'PASS' if ok else 'FAIL'} rc={rc}",
                f"- raw={raw_file}",
                f"- evidence_hits={ev['evidence_hits']} any_hits={ev['any_hits']}",
                f"- missing_all={ev['missing_all']}",
            ])
        q_lines.append(f"Conclusion: {'PASS' if q_ok else 'FAIL'}")

    q_lines.append("")
    sections[layer].append("\n".join(q_lines))

write_block(["# Code Graph RAG Results", ""])
for block in sections["code_graph"]:
    write_block([block])
write_block(["# Artifact RAG Results", ""])
for block in sections["artifact"]:
    write_block([block])
write_block(["# Mixed RAG Results", ""])
for block in sections["mixed"]:
    write_block([block])

write_block([
    "# Summary",
    f"total={summary['total']}",
    f"passed={summary['passed']}",
    f"failed={summary['failed']}",
    f"critical_failed={summary['critical_failed']}",
])

print(log_file)
if summary["critical_failed"] > 0:
    sys.exit(1)
PY

echo "Saved: $LOG_FILE"
