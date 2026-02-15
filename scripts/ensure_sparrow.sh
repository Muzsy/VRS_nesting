#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT_DIR"

log() {
  echo "$*" >&2
}

need_cmd() {
  local c="$1"
  if ! command -v "$c" >/dev/null 2>&1; then
    log "ERROR: required command not found: $c"
    exit 2
  fi
}

abs_path() {
  python3 - "$1" <<'PY'
from pathlib import Path
import sys
print(str(Path(sys.argv[1]).resolve()))
PY
}

resolve_bin_from_value() {
  local value="$1"
  local resolved=""

  if resolved="$(command -v "$value" 2>/dev/null)"; then
    if [[ -x "$resolved" ]]; then
      abs_path "$resolved"
      return 0
    fi
  fi

  if [[ -x "$value" ]]; then
    abs_path "$value"
    return 0
  fi

  return 1
}

build_and_return_bin() {
  local src_dir="$1"
  local label="$2"
  need_cmd cargo
  log "[ensure_sparrow] build source: $label ($src_dir)"
  (cd "$src_dir" && cargo build --release >&2)

  local bin="$src_dir/target/release/sparrow"
  if [[ ! -x "$bin" ]]; then
    log "ERROR: Sparrow binary missing or not executable after build: $bin"
    exit 2
  fi
  abs_path "$bin"
}

resolve_pin_commit() {
  local commit="${SPARROW_COMMIT:-}"
  if [[ -z "$commit" && -f "poc/sparrow_io/sparrow_commit.txt" ]]; then
    commit="$(tr -d '\n\r' < poc/sparrow_io/sparrow_commit.txt)"
  fi
  echo "$commit"
}

apply_pin_if_requested() {
  local src_dir="$1"
  local mode="$2"
  local allow_fetch="$3"
  local commit
  commit="$(resolve_pin_commit)"

  if [[ -z "$commit" ]]; then
    return 0
  fi

  if [[ ! -d "$src_dir/.git" ]]; then
    if [[ "$mode" == "vendor" ]]; then
      log "[ensure_sparrow] vendor/sparrow is not a git repo; skipping commit pin validation: $commit"
    fi
    return 0
  fi

  log "[ensure_sparrow] pin commit ($mode): $commit"
  if git -C "$src_dir" rev-parse --verify "${commit}^{commit}" >/dev/null 2>&1; then
    git -C "$src_dir" checkout "$commit" >&2
    return 0
  fi

  if [[ "$allow_fetch" == "1" ]]; then
    log "[ensure_sparrow] commit not available locally, fetching..."
    if git -C "$src_dir" fetch --all --tags --prune >&2 && \
       git -C "$src_dir" rev-parse --verify "${commit}^{commit}" >/dev/null 2>&1; then
      git -C "$src_dir" checkout "$commit" >&2
      return 0
    fi
    log "ERROR: pinned commit not available after fetch: $commit"
    exit 2
  fi

  log "ERROR: vendor/submodule Sparrow does not contain pinned commit: $commit"
  log "Teendo: frissitsd a submodule-t (git submodule update --init --recursive) vagy allitsd a megfelelo commitra."
  exit 2
}

# Priority 1: explicit SPARROW_BIN
if [[ -n "${SPARROW_BIN:-}" ]]; then
  if resolved_bin="$(resolve_bin_from_value "$SPARROW_BIN")"; then
    echo "$resolved_bin"
    exit 0
  fi
  log "ERROR: SPARROW_BIN is set but not executable/resolvable: $SPARROW_BIN"
  exit 2
fi

# Priority 2: explicit source dir
if [[ -n "${SPARROW_SRC_DIR:-}" ]]; then
  src_dir="$(abs_path "$SPARROW_SRC_DIR")"
  if [[ ! -f "$src_dir/Cargo.toml" ]]; then
    log "ERROR: SPARROW_SRC_DIR does not look like Sparrow source (missing Cargo.toml): $src_dir"
    exit 2
  fi
  apply_pin_if_requested "$src_dir" "src_env" "1"
  build_and_return_bin "$src_dir" "SPARROW_SRC_DIR"
  exit 0
fi

# Priority 3: vendor/submodule
if [[ -f "vendor/sparrow/Cargo.toml" ]]; then
  vendor_dir="$(abs_path "vendor/sparrow")"
  apply_pin_if_requested "$vendor_dir" "vendor" "0"
  build_and_return_bin "$vendor_dir" "vendor/sparrow"
  exit 0
fi

# Priority 4: fallback cache clone
need_cmd git
cache_dir="$(abs_path ".cache/sparrow")"
mkdir -p .cache
if [[ ! -d "$cache_dir/.git" ]]; then
  rm -rf "$cache_dir"
  log "[ensure_sparrow] fallback clone -> $cache_dir"
  git clone https://github.com/JeroenGar/sparrow.git "$cache_dir" >&2
fi

apply_pin_if_requested "$cache_dir" "fallback_cache" "1"
build_and_return_bin "$cache_dir" ".cache/sparrow"
