#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
STATE_DIR="${ROOT_DIR}/.cache/web_platform"
LOG_DIR="${STATE_DIR}/logs"
PID_DIR="${STATE_DIR}/pids"

API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
API_RELOAD="${API_RELOAD:-1}"
START_TIMEOUT_S="${START_TIMEOUT_S:-20}"

ENV_FILE=""

usage() {
  cat <<'USAGE'
Usage:
  ./scripts/run_web_platform.sh start
  ./scripts/run_web_platform.sh stop
  ./scripts/run_web_platform.sh restart
  ./scripts/run_web_platform.sh status
  ./scripts/run_web_platform.sh logs [api|worker|frontend]

Environment overrides:
  API_HOST, API_PORT
  FRONTEND_HOST, FRONTEND_PORT
  API_RELOAD=1|0
  START_TIMEOUT_S
USAGE
}

need_cmd() {
  local c="$1"
  if ! command -v "$c" >/dev/null 2>&1; then
    echo "ERROR: missing command: $c" >&2
    exit 2
  fi
}

pid_file_for() {
  local name="$1"
  echo "${PID_DIR}/${name}.pid"
}

log_file_for() {
  local name="$1"
  echo "${LOG_DIR}/${name}.log"
}

is_pid_running() {
  local pid="$1"
  [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1
}

read_pid() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]]; then
    tr -d '[:space:]' <"$pid_file"
  fi
}

ensure_dirs() {
  mkdir -p "$LOG_DIR" "$PID_DIR"
}

resolve_env_file() {
  if [[ -f "${ROOT_DIR}/.env.local" ]]; then
    ENV_FILE="${ROOT_DIR}/.env.local"
    return
  fi
  if [[ -f "${ROOT_DIR}/.env" ]]; then
    ENV_FILE="${ROOT_DIR}/.env"
    return
  fi
  ENV_FILE=""
}

load_env_if_present() {
  resolve_env_file
  if [[ -n "$ENV_FILE" ]]; then
    set -a
    # shellcheck source=/dev/null
    source "$ENV_FILE"
    set +a
  fi
}

apply_frontend_env_compat() {
  # Vite exposes only VITE_* vars to frontend code.
  # Map existing repo-level SUPABASE_* vars for local convenience.
  if [[ -z "${VITE_SUPABASE_URL:-}" && -n "${SUPABASE_URL:-}" ]]; then
    export VITE_SUPABASE_URL="$SUPABASE_URL"
  fi
  if [[ -z "${VITE_SUPABASE_ANON_KEY:-}" && -n "${SUPABASE_ANON_KEY:-}" ]]; then
    export VITE_SUPABASE_ANON_KEY="$SUPABASE_ANON_KEY"
  fi
  if [[ -z "${VITE_API_BASE_URL:-}" ]]; then
    export VITE_API_BASE_URL="http://${API_HOST}:${API_PORT}/v1"
  fi
}

apply_api_env_compat() {
  if [[ -z "${API_ALLOWED_ORIGINS:-}" ]]; then
    local alt_port=$((FRONTEND_PORT + 1))
    export API_ALLOWED_ORIGINS="http://127.0.0.1:${FRONTEND_PORT},http://localhost:${FRONTEND_PORT},http://127.0.0.1:${alt_port},http://localhost:${alt_port},http://localhost:3000"
  fi
}

start_service() {
  local name="$1"
  local workdir="$2"
  local cmd="$3"
  local pid_file
  local log_file
  local pid

  pid_file="$(pid_file_for "$name")"
  log_file="$(log_file_for "$name")"

  pid="$(read_pid "$pid_file" || true)"
  if is_pid_running "$pid"; then
    echo "[SKIP] ${name} already running (pid=${pid})"
    return 0
  fi

  rm -f "$pid_file"

  (
    cd "$workdir"
    nohup bash -lc "exec $cmd" >"$log_file" 2>&1 &
    echo $! >"$pid_file"
  )

  sleep 0.3
  pid="$(read_pid "$pid_file" || true)"
  if ! is_pid_running "$pid"; then
    echo "ERROR: failed to start ${name}. See log: ${log_file}" >&2
    tail -n 40 "$log_file" || true
    exit 2
  fi
  echo "[OK] ${name} started (pid=${pid}) log=${log_file}"
}

stop_service() {
  local name="$1"
  local pid_file
  local pid

  pid_file="$(pid_file_for "$name")"
  pid="$(read_pid "$pid_file" || true)"
  if ! is_pid_running "$pid"; then
    rm -f "$pid_file"
    echo "[SKIP] ${name} not running"
    return 0
  fi

  kill "$pid" >/dev/null 2>&1 || true
  for _ in $(seq 1 20); do
    if ! is_pid_running "$pid"; then
      rm -f "$pid_file"
      echo "[OK] ${name} stopped"
      return 0
    fi
    sleep 0.2
  done

  kill -9 "$pid" >/dev/null 2>&1 || true
  rm -f "$pid_file"
  echo "[OK] ${name} force-stopped"
}

cleanup_orphans() {
  # Best-effort cleanup for previously detached processes started by older script versions.
  pkill -f "uvicorn api.main:app --host ${API_HOST} --port ${API_PORT}" >/dev/null 2>&1 || true
  pkill -f "python3 -m worker.main" >/dev/null 2>&1 || true
  pkill -f "python3 worker/main.py" >/dev/null 2>&1 || true
  pkill -f "vite --host ${FRONTEND_HOST} --port ${FRONTEND_PORT}" >/dev/null 2>&1 || true
}

status_service() {
  local name="$1"
  local pid_file
  local pid

  pid_file="$(pid_file_for "$name")"
  pid="$(read_pid "$pid_file" || true)"
  if is_pid_running "$pid"; then
    echo "${name}: RUNNING (pid=${pid}) log=$(log_file_for "$name")"
  else
    echo "${name}: STOPPED"
  fi
}

wait_http_ready() {
  local url="$1"
  local label="$2"
  local timeout="$3"
  local start
  local now
  start="$(date +%s)"
  while true; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "[OK] ${label} ready: ${url}"
      return 0
    fi
    now="$(date +%s)"
    if (( now - start >= timeout )); then
      echo "ERROR: timeout waiting for ${label}: ${url}" >&2
      return 1
    fi
    sleep 0.5
  done
}

WORKER_READY_FILE="${STATE_DIR}/worker.ready"

wait_worker_ready() {
  local timeout="$1"
  local start
  local now
  start="$(date +%s)"
  while true; do
    if [[ -f "$WORKER_READY_FILE" ]]; then
      echo "[OK] worker ready: ${WORKER_READY_FILE}"
      return 0
    fi
    now="$(date +%s)"
    if (( now - start >= timeout )); then
      echo "ERROR: timeout waiting for worker readiness (${WORKER_READY_FILE})" >&2
      local worker_log
      worker_log="$(log_file_for worker)"
      if [[ -f "$worker_log" ]]; then
        echo "--- last 20 lines of worker log ---" >&2
        tail -n 20 "$worker_log" >&2 || true
      fi
      return 1
    fi
    sleep 0.5
  done
}

start_all() {
  need_cmd bash
  need_cmd curl
  need_cmd python3
  need_cmd npm
  need_cmd uvicorn
  ensure_dirs
  load_env_if_present
  apply_frontend_env_compat
  apply_api_env_compat

  local api_cmd="uvicorn api.main:app --host ${API_HOST} --port ${API_PORT}"
  if [[ "$API_RELOAD" == "1" ]]; then
    api_cmd="${api_cmd} --reload"
  fi

  rm -f "$WORKER_READY_FILE"

  start_service "api" "$ROOT_DIR" "$api_cmd"
  start_service "worker" "$ROOT_DIR" "python3 -m worker.main"
  start_service "frontend" "${ROOT_DIR}/frontend" "npm run dev -- --host ${FRONTEND_HOST} --port ${FRONTEND_PORT} --strictPort"

  wait_http_ready "http://${API_HOST}:${API_PORT}/health" "api" "$START_TIMEOUT_S"
  wait_worker_ready "$START_TIMEOUT_S"
  wait_http_ready "http://${FRONTEND_HOST}:${FRONTEND_PORT}/" "frontend" "$START_TIMEOUT_S"

  echo ""
  echo "Web platform started:"
  echo "  API:      http://${API_HOST}:${API_PORT}"
  echo "  Frontend: http://${FRONTEND_HOST}:${FRONTEND_PORT}"
  if [[ -n "$ENV_FILE" ]]; then
    echo "  Env file: ${ENV_FILE}"
  else
    echo "  Env file: (none loaded)"
  fi
}

stop_all() {
  stop_service "frontend"
  stop_service "worker"
  stop_service "api"
  rm -f "$WORKER_READY_FILE"
  cleanup_orphans
}

logs_cmd() {
  local svc="${1:-}"
  if [[ -z "$svc" ]]; then
    echo "ERROR: logs requires service name: api|worker|frontend" >&2
    exit 2
  fi
  case "$svc" in
    api|worker|frontend) ;;
    *)
      echo "ERROR: unknown service: $svc" >&2
      exit 2
      ;;
  esac
  local log_file
  log_file="$(log_file_for "$svc")"
  if [[ ! -f "$log_file" ]]; then
    echo "No log yet: ${log_file}"
    exit 0
  fi
  tail -n 80 "$log_file"
}

main() {
  local cmd="${1:-}"
  case "$cmd" in
    start)
      start_all
      ;;
    stop)
      stop_all
      ;;
    restart)
      stop_all
      start_all
      ;;
    status)
      status_service "api"
      status_service "worker"
      status_service "frontend"
      ;;
    logs)
      logs_cmd "${2:-}"
      ;;
    -h|--help|help|"")
      usage
      ;;
    *)
      echo "ERROR: unknown command: $cmd" >&2
      usage
      exit 2
      ;;
  esac
}

main "$@"
