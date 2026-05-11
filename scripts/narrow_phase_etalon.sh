#!/usr/bin/env bash
# Etalon benchmark for own narrow-phase optimizations.
#
# Produces a fully reproducible measurement: build release, microbench, LV8
# full-CFR, LV8 subset active-set. Parses NEST_NFP_STATS_V1 into metrics.json
# and appends a row to tmp/etalon/SUMMARY.md so successive optimizations are
# trivially comparable.
#
# Usage:
#   scripts/narrow_phase_etalon.sh <label>
#
# Example:
#   scripts/narrow_phase_etalon.sh baseline_t06o
#   scripts/narrow_phase_etalon.sh t06p_ring_aabb

set -euo pipefail
export LC_NUMERIC=C
export LC_ALL=C

LABEL="${1:-}"
if [[ -z "$LABEL" ]]; then
  echo "usage: $0 <label>" >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

ETALON_DIR="$REPO_ROOT/tmp/etalon"
INPUTS_DIR="$ETALON_DIR/inputs"
RESULTS_DIR="$ETALON_DIR/results"
LV8_INPUT="$INPUTS_DIR/lv8_prepacked.json"
SUBSET_INPUT="$INPUTS_DIR/lv8_subset_4parts_q5.json"
SUMMARY_MD="$ETALON_DIR/SUMMARY.md"
CGAL_PROBE="$REPO_ROOT/tools/nfp_cgal_probe/build/nfp_cgal_probe"

for f in "$LV8_INPUT" "$SUBSET_INPUT" "$CGAL_PROBE"; do
  if [[ ! -e "$f" ]]; then
    echo "ERROR: required path missing: $f" >&2
    exit 2
  fi
done

TS="$(date -u +%Y%m%dT%H%M%SZ)"
GIT_COMMIT="$(git rev-parse --short HEAD)"
GIT_DIRTY="$(git status --porcelain | wc -l)"
SEQ="$(printf '%02d' $(find "$RESULTS_DIR" -maxdepth 1 -mindepth 1 -type d 2>/dev/null | wc -l))"
RUN_DIR="$RESULTS_DIR/${SEQ}_${LABEL}_${TS}"
mkdir -p "$RUN_DIR"

log() { echo "[etalon] $*" | tee -a "$RUN_DIR/etalon.log"; }

log "=== Etalon run ==="
log "label:     $LABEL"
log "timestamp: $TS"
log "git:       $GIT_COMMIT (dirty_files=$GIT_DIRTY)"
log "run_dir:   $RUN_DIR"
log ""

# 1) Build release
log "[1/4] Building release..."
build_start=$(date +%s%N)
(cd rust/nesting_engine && cargo build --release -p nesting_engine 2>&1) \
  > "$RUN_DIR/build.log" 2>&1
build_ns=$(( $(date +%s%N) - build_start ))
log "      build_ms=$(( build_ns / 1000000 ))"

# 2) Microbenchmark
log "[2/4] Microbench 50000 pairs..."
rust/nesting_engine/target/release/narrow_phase_bench --mode microbench --pairs 50000 \
  > "$RUN_DIR/microbench.log" 2>&1

# 3) LV8 full-CFR (Run A equivalent)
log "[3/4] LV8 full-CFR (search=none, profile on, cgal_reference)..."
lv8_start=$(date +%s%N)
set +e
NESTING_ENGINE_NARROW_PHASE=own \
NESTING_ENGINE_CAN_PLACE_PROFILE=1 \
NESTING_ENGINE_EMIT_NFP_STATS=1 \
NESTING_ENGINE_ACTIVE_SET_CANDIDATES=0 \
NESTING_ENGINE_HYBRID_CFR=0 \
NESTING_ENGINE_CFR_DIAG=0 \
NESTING_ENGINE_NFP_RUNTIME_DIAG=0 \
NFP_ENABLE_CGAL_REFERENCE=1 \
NFP_CGAL_PROBE_BIN="$CGAL_PROBE" \
NESTING_ENGINE_NFP_KERNEL=cgal_reference \
timeout 360 rust/nesting_engine/target/release/nesting_engine nest \
  --placer nfp --search none --part-in-part off --compaction off \
  --nfp-kernel cgal_reference \
  < "$LV8_INPUT" \
  > "$RUN_DIR/lv8_full_cfr.stdout.json" \
  2> "$RUN_DIR/lv8_full_cfr.stderr.log"
LV8_EXIT=$?
set -e
lv8_ms=$(( ($(date +%s%N) - lv8_start) / 1000000 ))
log "      lv8_full_cfr exit=$LV8_EXIT wallclock_ms=$lv8_ms"

# 4) Subset active-set + full fallback (Run E_B equivalent)
log "[4/4] Subset active-set + full fallback..."
subset_start=$(date +%s%N)
set +e
NESTING_ENGINE_NARROW_PHASE=own \
NESTING_ENGINE_CAN_PLACE_PROFILE=1 \
NESTING_ENGINE_EMIT_NFP_STATS=1 \
NESTING_ENGINE_ACTIVE_SET_CANDIDATES=1 \
NESTING_ENGINE_ACTIVE_SET_LOCAL_CFR_FALLBACK=1 \
NESTING_ENGINE_ACTIVE_SET_FULL_CFR_FALLBACK=1 \
NFP_ENABLE_CGAL_REFERENCE=1 \
NFP_CGAL_PROBE_BIN="$CGAL_PROBE" \
NESTING_ENGINE_NFP_KERNEL=cgal_reference \
timeout 180 rust/nesting_engine/target/release/nesting_engine nest \
  --placer nfp --search none --part-in-part off --compaction off \
  --nfp-kernel cgal_reference \
  < "$SUBSET_INPUT" \
  > "$RUN_DIR/subset_active_set.stdout.json" \
  2> "$RUN_DIR/subset_active_set.stderr.log"
SUBSET_EXIT=$?
set -e
subset_ms=$(( ($(date +%s%N) - subset_start) / 1000000 ))
log "      subset_active_set exit=$SUBSET_EXIT wallclock_ms=$subset_ms"

# Parse metrics
log "[parse] extracting metrics..."

mb_own_nspair=$(awk '/^ns\/pair:/ {print $2; exit}' "$RUN_DIR/microbench.log")
mb_iovr_nspair=$(awk '/^ns\/pair:/ {print $3; exit}' "$RUN_DIR/microbench.log")
mb_own_ms=$(awk '/^Runtime ms:/ {print $3; exit}' "$RUN_DIR/microbench.log")
mb_iovr_ms=$(awk '/^Runtime ms:/ {print $4; exit}' "$RUN_DIR/microbench.log")
mb_collisions=$(awk '/^Collision count:/ {print $3; exit}' "$RUN_DIR/microbench.log")
mb_false=$(awk '/^False accepts:/ {print $3; exit}' "$RUN_DIR/microbench.log")

parse_stats() {
  local stderr_file="$1"
  if grep -q "^NEST_NFP_STATS_V1" "$stderr_file"; then
    grep "^NEST_NFP_STATS_V1" "$stderr_file" | tail -1 | sed 's/^NEST_NFP_STATS_V1 //'
  else
    echo "null"
  fi
}

LV8_STATS=$(parse_stats "$RUN_DIR/lv8_full_cfr.stderr.log")
SUBSET_STATS=$(parse_stats "$RUN_DIR/subset_active_set.stderr.log")

LV8_PLACED=$(jq -r '.placements | length' "$RUN_DIR/lv8_full_cfr.stdout.json" 2>/dev/null || echo "null")
LV8_UNPLACED=$(jq -r '.unplaced | length' "$RUN_DIR/lv8_full_cfr.stdout.json" 2>/dev/null || echo "null")
LV8_SHEETS=$(jq -r '.sheets_used // null' "$RUN_DIR/lv8_full_cfr.stdout.json" 2>/dev/null || echo "null")
LV8_UTIL=$(jq -r '.objective.utilization_pct // null' "$RUN_DIR/lv8_full_cfr.stdout.json" 2>/dev/null || echo "null")
LV8_HASH=$(jq -r '.meta.determinism_hash // null' "$RUN_DIR/lv8_full_cfr.stdout.json" 2>/dev/null || echo "null")
SUBSET_PLACED=$(jq -r '.placements | length' "$RUN_DIR/subset_active_set.stdout.json" 2>/dev/null || echo "null")
SUBSET_UNPLACED=$(jq -r '.unplaced | length' "$RUN_DIR/subset_active_set.stdout.json" 2>/dev/null || echo "null")
SUBSET_HASH=$(jq -r '.meta.determinism_hash // null' "$RUN_DIR/subset_active_set.stdout.json" 2>/dev/null || echo "null")

# Build metrics.json
jq -n \
  --arg label "$LABEL" \
  --arg ts "$TS" \
  --arg git_commit "$GIT_COMMIT" \
  --arg git_dirty "$GIT_DIRTY" \
  --argjson lv8_exit "$LV8_EXIT" --argjson lv8_wallclock_ms "$lv8_ms" \
  --argjson subset_exit "$SUBSET_EXIT" --argjson subset_wallclock_ms "$subset_ms" \
  --argjson lv8_stats "$LV8_STATS" \
  --argjson subset_stats "$SUBSET_STATS" \
  --argjson lv8_placed "$LV8_PLACED" --argjson lv8_unplaced "$LV8_UNPLACED" \
  --argjson lv8_sheets "$LV8_SHEETS" --argjson lv8_util "$LV8_UTIL" \
  --arg lv8_hash "$LV8_HASH" \
  --argjson subset_placed "$SUBSET_PLACED" --argjson subset_unplaced "$SUBSET_UNPLACED" \
  --arg subset_hash "$SUBSET_HASH" \
  --arg mb_own_nspair "$mb_own_nspair" --arg mb_iovr_nspair "$mb_iovr_nspair" \
  --arg mb_own_ms "$mb_own_ms" --arg mb_iovr_ms "$mb_iovr_ms" \
  --arg mb_collisions "$mb_collisions" --arg mb_false "$mb_false" \
  '{
    label: $label, timestamp: $ts, git_commit: $git_commit, git_dirty: $git_dirty,
    microbench: {
      own_ns_per_pair: ($mb_own_nspair | tonumber),
      i_overlay_ns_per_pair: ($mb_iovr_nspair | tonumber),
      own_runtime_ms: ($mb_own_ms | tonumber),
      i_overlay_runtime_ms: ($mb_iovr_ms | tonumber),
      collision_count: ($mb_collisions | tonumber),
      false_accepts: ($mb_false | tonumber)
    },
    lv8_full_cfr: {
      exit: $lv8_exit, wallclock_ms: $lv8_wallclock_ms,
      placed: $lv8_placed, unplaced: $lv8_unplaced, sheets: $lv8_sheets,
      utilization_pct: $lv8_util, determinism_hash: $lv8_hash,
      stats: $lv8_stats
    },
    subset_active_set: {
      exit: $subset_exit, wallclock_ms: $subset_wallclock_ms,
      placed: $subset_placed, unplaced: $subset_unplaced,
      determinism_hash: $subset_hash,
      stats: $subset_stats
    }
  }' > "$RUN_DIR/metrics.json"

# Append summary row
if [[ ! -f "$SUMMARY_MD" ]]; then
  cat > "$SUMMARY_MD" <<'EOF'
# Narrow-phase etalon results

Updated automatically by `scripts/narrow_phase_etalon.sh <label>`.

| Seq | Label | Git | Microbench own ns/pair | LV8 narrow_ms | LV8 total_ms | LV8 narrow_pairs | LV8 segpair_actual | LV8 placed | LV8 sheets | LV8 util % | LV8 hash | LV8 wallclock_ms | Subset narrow_ms | Subset wallclock_ms | Subset hash |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---|
EOF
fi

# Extract row metrics
lv8_narrow_ms=$(jq -r '.lv8_full_cfr.stats.can_place_profile_narrow_phase_ns_total // 0 | . / 1e6' "$RUN_DIR/metrics.json")
lv8_total_ms=$(jq -r '.lv8_full_cfr.stats.can_place_profile_total_ns // 0 | . / 1e6' "$RUN_DIR/metrics.json")
lv8_narrow_pairs=$(jq -r '.lv8_full_cfr.stats.can_place_profile_narrow_phase_pair_count_total // "n/a"' "$RUN_DIR/metrics.json")
lv8_segpair_actual=$(jq -r '.lv8_full_cfr.stats.can_place_profile_segment_pair_actual_total // "n/a"' "$RUN_DIR/metrics.json")
sub_narrow_ms=$(jq -r '.subset_active_set.stats.can_place_profile_narrow_phase_ns_total // 0 | . / 1e6' "$RUN_DIR/metrics.json")

printf '| %s | %s | %s | %.1f | %.1f | %.1f | %s | %s | %s | %s | %s | %s | %s | %.1f | %s | %s |\n' \
  "$SEQ" "$LABEL" "$GIT_COMMIT" \
  "$mb_own_nspair" "$lv8_narrow_ms" "$lv8_total_ms" "$lv8_narrow_pairs" "$lv8_segpair_actual" \
  "$LV8_PLACED" "$LV8_SHEETS" "$LV8_UTIL" "$(echo "$LV8_HASH" | cut -c8-15)" "$lv8_ms" \
  "$sub_narrow_ms" "$subset_ms" "$(echo "$SUBSET_HASH" | cut -c8-15)" \
  >> "$SUMMARY_MD"

log ""
log "=== Done ==="
log "metrics: $RUN_DIR/metrics.json"
log "summary: $SUMMARY_MD"
log ""
log "Key numbers for this run:"
log "  microbench own:         $mb_own_nspair ns/pair (false_accepts=$mb_false)"
log "  LV8 narrow_phase_ms:    $lv8_narrow_ms"
log "  LV8 total_ms:           $lv8_total_ms"
log "  LV8 wallclock_ms:       $lv8_ms"
log "  LV8 placed/unplaced:    $LV8_PLACED / $LV8_UNPLACED   (sheets=$LV8_SHEETS, util=$LV8_UTIL%)"
log "  LV8 det.hash:           $LV8_HASH"
log "  subset narrow_phase_ms: $sub_narrow_ms"
log "  subset wallclock_ms:    $subset_ms"
log "  subset det.hash:        $SUBSET_HASH"
