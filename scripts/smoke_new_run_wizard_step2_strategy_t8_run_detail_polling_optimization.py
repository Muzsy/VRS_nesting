#!/usr/bin/env python3
"""
Offline source-level smoke for T8: Run Detail polling optimization.
No DB, Supabase, worker, solver binary, or node_modules required.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

passed: list[str] = []
failed: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        passed.append(name)
        print(f"  PASS  {name}")
    else:
        failed.append(name)
        print(f"  FAIL  {name}" + (f" — {detail}" if detail else ""))


def read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. RunDetailPage — polling guard and viewer-data once-only fetch
# ---------------------------------------------------------------------------
print("\n[1] frontend/src/pages/RunDetailPage.tsx — polling guard")

run_detail_path = REPO_ROOT / "frontend" / "src" / "pages" / "RunDetailPage.tsx"
check("RunDetailPage exists", run_detail_path.exists())

run_detail_src = read(run_detail_path)

# Explicit once/attempted guard
check(
    "RunDetailPage: viewerDataAttemptedRef guard present",
    "viewerDataAttemptedRef" in run_detail_src,
)
check(
    "RunDetailPage: viewerDataAttemptedRef.current check before fetch",
    "viewerDataAttemptedRef.current" in run_detail_src,
)

# Terminal status condition for viewer-data fetch
check(
    "RunDetailPage: terminal condition guards viewer-data",
    ("runIsTerminal" in run_detail_src or "isTerminal" in run_detail_src) and "viewerDataAttemptedRef" in run_detail_src,
)

# isTerminalRef used to avoid stale closure in timer callback
check(
    "RunDetailPage: isTerminalRef present (avoids stale run closure)",
    "isTerminalRef" in run_detail_src,
)
check(
    "RunDetailPage: isTerminalRef.current used in timer",
    "isTerminalRef.current" in run_detail_src,
)

# Viewer-data error must stay non-fatal (no setError inside the viewer-data catch block)
# Check that the viewer-data catch block does NOT call setError
vd_section_start = run_detail_src.find("getViewerData")
vd_catch_start = run_detail_src.find("} catch", vd_section_start) if vd_section_start >= 0 else -1
vd_catch_end = run_detail_src.find("}", vd_catch_start + 1) if vd_catch_start >= 0 else -1
vd_inner_catch = run_detail_src[vd_catch_start:vd_catch_end] if vd_catch_start >= 0 and vd_catch_end >= 0 else ""
check(
    "RunDetailPage: viewer-data catch block is non-fatal (no setError)",
    "setError" not in vd_inner_catch or vd_inner_catch == "",
)

# Guard reset on projectId/runId change
check(
    "RunDetailPage: viewerDataAttemptedRef reset in useEffect cleanup",
    "viewerDataAttemptedRef.current = false" in run_detail_src,
)
check(
    "RunDetailPage: isTerminalRef reset in useEffect cleanup",
    "isTerminalRef.current = false" in run_detail_src,
)

# ---------------------------------------------------------------------------
# 2. T5/T7 audit UI texts preserved
# ---------------------------------------------------------------------------
print("\n[2] frontend/src/pages/RunDetailPage.tsx — T5/T7 audit UI preserved")

check("RunDetailPage: Strategy and engine audit heading", "Strategy and engine audit" in run_detail_src)
check("RunDetailPage: Not available yet fallback", "Not available yet" in run_detail_src)
check("RunDetailPage: Strategy field sources", "Strategy field sources" in run_detail_src)
check("RunDetailPage: No field source evidence fallback", "No field source evidence" in run_detail_src)
check("RunDetailPage: requested_engine_backend field shown", "requested_engine_backend" in run_detail_src)
check("RunDetailPage: effective_engine_backend field shown", "effective_engine_backend" in run_detail_src)
check("RunDetailPage: strategy_profile_version_id field shown", "strategy_profile_version_id" in run_detail_src)

# ---------------------------------------------------------------------------
# 3. T8 E2E spec
# ---------------------------------------------------------------------------
print("\n[3] T8 Playwright spec")

t8_spec_path = REPO_ROOT / "frontend" / "e2e" / "new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.spec.ts"
check("T8 spec exists", t8_spec_path.exists())

if t8_spec_path.exists():
    t8_src = t8_spec_path.read_text(encoding="utf-8")
    check("T8 spec: done-once test case present", "done" in t8_src and ("once" in t8_src.lower() or "viewer-data" in t8_src.lower()))
    check("T8 spec: running-no-viewer-data test case present", "running" in t8_src and "viewer" in t8_src.lower())
    check("T8 spec: request counting with page.on", 'page.on("request"' in t8_src or "page.on('request'" in t8_src)
    check("T8 spec: viewerDataRequestCount variable", "viewerDataRequestCount" in t8_src)
    check("T8 spec: waitForTimeout for polling cycle", "waitForTimeout" in t8_src)
    check("T8 spec: asserts count <= 1 for done run", "LessThanOrEqual(1)" in t8_src or "<= 1" in t8_src or "toBe(1)" in t8_src)
    check("T8 spec: asserts count === 0 for running run", "toBe(0)" in t8_src)
    check("T8 spec: RUNNING status assertion", "RUNNING" in t8_src)
    check("T8 spec: uses installMockApi", "installMockApi" in t8_src)
    check("T8 spec: Strategy and engine audit assertion", "Strategy and engine audit" in t8_src)

# ---------------------------------------------------------------------------
# 4. Rollout doc — polling limitation marked as covered
# ---------------------------------------------------------------------------
print("\n[4] Rollout doc — polling optimization no longer an open limitation")

rollout_path = REPO_ROOT / "docs" / "web_platform" / "architecture" / "new_run_wizard_step2_strategy_rollout_and_compatibility_plan.md"
check("Rollout doc exists", rollout_path.exists())

if rollout_path.exists():
    rdoc = rollout_path.read_text(encoding="utf-8")
    # Old open limitation phrases must be gone
    old_phrases = [
        "Run Detail polling is not yet optimized",
        "viewer-data is fetched unconditionally",
        "viewer-data called every 3 s",
        "polling optimization is not yet",
    ]
    for phrase in old_phrases:
        check(
            f"Rollout doc: open polling limitation phrase absent: {phrase[:60]!r}",
            phrase not in rdoc,
            f"still contains: {phrase!r}",
        )
    # Should mention T8 covered it
    check(
        "Rollout doc: T8 polling optimization mentioned as covered",
        "T8" in rdoc and ("once" in rdoc.lower() or "terminal" in rdoc.lower() or "non-fatal" in rdoc.lower()),
    )

# ---------------------------------------------------------------------------
# 5. Artefakt-fegyelem — T8 saját alkönyvtár, nincs root-level duplikátum
# ---------------------------------------------------------------------------
print("\n[5] Artefakt-fegyelem — T8 saját alkönyvtár, nincs root-level duplikátum")

t8_slug = "new_run_wizard_step2_strategy_t8_run_detail_polling_optimization"
check("T8 canvas dir exists", (REPO_ROOT / "canvases" / "web_platform" / t8_slug).is_dir())
check("T8 goal yaml dir exists", (REPO_ROOT / "codex" / "goals" / "canvases" / "web_platform" / t8_slug).is_dir())
check("T8 runner prompt dir exists", (REPO_ROOT / "codex" / "prompts" / "web_platform" / t8_slug).is_dir())

canvas_root = REPO_ROOT / "canvases" / "web_platform"
root_md = list(canvas_root.glob("new_run_wizard_step2_strategy_t8*.md"))
check("No root-level T8 canvas .md duplicate", len(root_md) == 0, f"found: {[f.name for f in root_md]}")

goals_root = REPO_ROOT / "codex" / "goals" / "canvases" / "web_platform"
root_yaml = list(goals_root.glob("new_run_wizard_step2_strategy_t8*.yaml"))
check("No root-level T8 goal yaml duplicate", len(root_yaml) == 0, f"found: {[f.name for f in root_yaml]}")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
total = len(passed) + len(failed)
print(f"\n{'='*60}")
if failed:
    print(f"FAIL: {len(failed)} check(s) failed, {len(passed)} passed ({total} total)")
    for name in failed:
        print(f"  - {name}")
    sys.exit(1)
else:
    print(f"PASS: {len(passed)} checks passed ({total} total)")
    sys.exit(0)
