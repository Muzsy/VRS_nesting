#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  ./scripts/verify.sh --report <path/to/report.md>
  ./scripts/verify.sh --report <path/to/report.md> [--tail-lines <N>] [--no-cd-root]

What it does:
  - Runs the repo's standard quality gate: ./scripts/check.sh
  - Writes a log next to the report: <report>.verify.log (same basename, .md removed)
  - Updates an auto-managed block inside the report between markers:
      <!-- AUTO_VERIFY_START -->
      <!-- AUTO_VERIFY_END -->
  - (Default) cd's to repo root so it can be run from anywhere

Intended use:
  - The *last* step of every Codex canvas+YAML run.

Exit codes:
  - 0  on PASS
  - 1  on FAIL (check.sh failed)
  - 2  on usage / missing files
USAGE
}

REPORT=""
TAIL_LINES="60"
CD_TO_ROOT="1"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --report)
      REPORT="${2:-}"
      shift 2
      ;;
    --tail-lines)
      TAIL_LINES="${2:-}"
      shift 2
      ;;
    --no-cd-root)
      CD_TO_ROOT="0"
      shift 1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "${REPORT}" ]]; then
  echo "ERROR: --report is required." >&2
  usage
  exit 2
fi

if [[ -z "${TAIL_LINES}" || ! "${TAIL_LINES}" =~ ^[0-9]+$ || "${TAIL_LINES}" -lt 1 ]]; then
  echo "ERROR: --tail-lines must be a positive integer (got: ${TAIL_LINES})." >&2
  exit 2
fi

if [[ ! -f "${REPORT}" ]]; then
  echo "ERROR: Report file not found: ${REPORT}" >&2
  echo "Create it first (per docs/codex/report_standard.md), then re-run verify." >&2
  exit 2
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found. verify.sh requires python3 to update the report block." >&2
  exit 2
fi

# Stabilize REPORT to an absolute path (so optional cd won't change its meaning).
REPORT_DIR="$(cd "$(dirname "${REPORT}")" && pwd -P)"
REPORT_BASE="$(basename "${REPORT}")"
REPORT="${REPORT_DIR}/${REPORT_BASE}"

# Optionally cd to repo root (best-effort), so the script works from any cwd.
if [[ "${CD_TO_ROOT}" -eq 1 ]]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
  ROOT_FROM_SCRIPT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
  if [[ -x "${ROOT_FROM_SCRIPT}/scripts/check.sh" ]]; then
    cd "${ROOT_FROM_SCRIPT}"
  elif command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
    if [[ -n "${REPO_ROOT}" && -x "${REPO_ROOT}/scripts/check.sh" ]]; then
      cd "${REPO_ROOT}"
    fi
  fi
fi

if [[ ! -x "./scripts/check.sh" ]]; then
  echo "ERROR: ./scripts/check.sh not found or not executable." >&2
  exit 2
fi

LOG_BASE="${REPORT%.md}"
LOG="${LOG_BASE}.verify.log"

mkdir -p "$(dirname "${REPORT}")"
mkdir -p "$(dirname "${LOG}")"

START_ISO="$(date -Iseconds)"
START_EPOCH="$(date +%s)"

# Collect git info (best-effort).
GIT_BRANCH=""
GIT_SHA=""
GIT_SHORT=""
if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  GIT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
  GIT_SHA="$(git rev-parse HEAD 2>/dev/null || true)"
  GIT_SHORT="$(git rev-parse --short HEAD 2>/dev/null || true)"
fi

# Run the standard gate and capture output.
set +e
./scripts/check.sh 2>&1 | tee "${LOG}"
CHECK_EXIT="${PIPESTATUS[0]}"
set -e

END_ISO="$(date -Iseconds)"
END_EPOCH="$(date +%s)"
DURATION_SEC="$(( END_EPOCH - START_EPOCH ))"

RESULT="FAIL"
if [[ "${CHECK_EXIT}" -eq 0 ]]; then
  RESULT="PASS"
fi

# Small, useful context for the report (best-effort).
DIFF_STAT=""
STATUS_PORCELAIN=""
if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  DIFF_STAT="$(git diff --stat 2>/dev/null || true)"
  STATUS_PORCELAIN="$(git status --porcelain 2>/dev/null || true)"
fi

FAIL_TAIL=""
if [[ "${RESULT}" != "PASS" ]]; then
  # Keep it short; the full log is in the .verify.log file.
  FAIL_TAIL="$(tail -n "${TAIL_LINES}" "${LOG}" 2>/dev/null || true)"
fi

export VERIFY_REPORT="${REPORT}"
export VERIFY_LOG="${LOG}"
export VERIFY_RESULT="${RESULT}"
export VERIFY_CHECK_EXIT="${CHECK_EXIT}"
export VERIFY_START_ISO="${START_ISO}"
export VERIFY_END_ISO="${END_ISO}"
export VERIFY_DURATION_SEC="${DURATION_SEC}"
export VERIFY_GIT_BRANCH="${GIT_BRANCH}"
export VERIFY_GIT_SHA="${GIT_SHA}"
export VERIFY_GIT_SHORT="${GIT_SHORT}"
export VERIFY_DIFF_STAT="${DIFF_STAT}"
export VERIFY_STATUS_PORCELAIN="${STATUS_PORCELAIN}"
export VERIFY_FAIL_TAIL="${FAIL_TAIL}"
export VERIFY_TAIL_LINES="${TAIL_LINES}"

python3 - <<'PY'
import os
import re
from pathlib import Path

report = Path(os.environ["VERIFY_REPORT"])
log = os.environ["VERIFY_LOG"]
result = os.environ["VERIFY_RESULT"]
check_exit = os.environ.get("VERIFY_CHECK_EXIT","" ).strip()
start_iso = os.environ["VERIFY_START_ISO"]
end_iso = os.environ["VERIFY_END_ISO"]
duration = os.environ["VERIFY_DURATION_SEC"]
position = os.environ.get("VERIFY_TAIL_LINES","60").strip()
if not position.isdigit():
  position = "60"
tail_lines = position
git_branch = os.environ.get("VERIFY_GIT_BRANCH","" ).strip()
git_short = os.environ.get("VERIFY_GIT_SHORT","" ).strip()
diff_stat = os.environ.get("VERIFY_DIFF_STAT","" ).rstrip()
status_porcelain = os.environ.get("VERIFY_STATUS_PORCELAIN","" ).rstrip()
fail_tail = os.environ.get("VERIFY_FAIL_TAIL","" ).rstrip()

changed_count = 0
changed_preview = ""
if status_porcelain:
  lines = status_porcelain.splitlines()
  changed_count = len(lines)
  changed_preview = "\n".join(lines[:60])

git_line = ""
if git_branch and git_short:
  git_line = f"{git_branch}@{git_short}"
elif git_short:
  git_line = git_short

block_lines = []
block_lines.append("<!-- AUTO_VERIFY_START -->")
block_lines.append("### Automatikus repo gate (verify.sh)")
block_lines.append("")
block_lines.append(f"- eredmény: **{result}**")
if check_exit:
  block_lines.append(f"- check.sh exit kód: `{check_exit}`")
block_lines.append(f"- futás: {start_iso} → {end_iso} ({duration}s)")
block_lines.append(f"- parancs: `./scripts/check.sh`")
block_lines.append(f"- log: `{log}`")
if git_line:
  block_lines.append(f"- git: `{git_line}`")
if changed_count:
  block_lines.append(f"- módosított fájlok (git status): {changed_count}")
block_lines.append("")

if diff_stat.strip():
  block_lines.append("**git diff --stat**")
  block_lines.append("")
  block_lines.append("```text")
  block_lines.extend(diff_stat.splitlines()[:200])
  block_lines.append("```")
  block_lines.append("")

if changed_preview.strip():
  block_lines.append("**git status --porcelain (preview)**")
  block_lines.append("")
  block_lines.append("```text")
  block_lines.extend(changed_preview.splitlines())
  block_lines.append("```")
  block_lines.append("")

if result != "PASS" and fail_tail.strip():
  block_lines.append(f"**FAIL tail (utolsó ~{tail_lines} sor a logból)**")
  block_lines.append("")
  block_lines.append("```text")
  block_lines.extend(fail_tail.splitlines())
  block_lines.append("```")
  block_lines.append("")

block_lines.append("<!-- AUTO_VERIFY_END -->")
block = "\n".join(block_lines) + "\n"

text = report.read_text(encoding="utf-8")

start_marker = "<!-- AUTO_VERIFY_START -->"
end_marker = "<!-- AUTO_VERIFY_END -->"

if start_marker in text and end_marker in text:
  pattern = re.compile(re.escape(start_marker) + r".*?" + re.escape(end_marker), re.DOTALL)
  text = pattern.sub(block.strip(), text)
  if not text.endswith("\n"):
    text += "\n"
else:
  if not text.endswith("\n"):
    text += "\n"
  text += "\n" + block

report.write_text(text, encoding="utf-8")
PY

if [[ "${CHECK_EXIT}" -eq 0 ]]; then
  exit 0
fi
exit 1
