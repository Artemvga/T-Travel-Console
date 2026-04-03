#!/bin/sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
FRONTEND_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
ROOT_DIR=$(CDPATH= cd -- "$FRONTEND_DIR/.." && pwd)
BACKEND_DIR="$ROOT_DIR/backend"
BACKEND_STARTED_BY_SCRIPT=0
SEED_TICKET_LIMIT="${T_TRAVEL_MAX_TICKETS_PER_FILE:-}"
BACKEND_HOST="127.0.0.1"
BACKEND_PORT=""

cleanup() {
  if [ "${BACKEND_STARTED_BY_SCRIPT:-0}" = "1" ] && [ "${BACKEND_PID:-}" != "" ]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
}

is_port_listening() {
  lsof -ti tcp:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

is_backend_ready() {
  curl -fsS "http://${BACKEND_HOST}:$1/api/health/" >/dev/null 2>&1
}

wait_for_backend() {
  attempts=0
  while [ "$attempts" -lt 60 ]; do
    if is_backend_ready "$1"; then
      return 0
    fi
    attempts=$((attempts + 1))
    sleep 0.25
  done
  return 1
}

find_backend_port() {
  for candidate in 8000 8001 8002 8003; do
    if is_backend_ready "$candidate"; then
      echo "$candidate"
      return 0
    fi
  done

  for candidate in 8000 8001 8002 8003; do
    if ! is_port_listening "$candidate"; then
      echo "$candidate"
      return 0
    fi
  done

  return 1
}

trap cleanup EXIT INT TERM

cd "$BACKEND_DIR"
if ! ./.venv/bin/python manage.py shell -c "from apps.tickets.models import Ticket; raise SystemExit(0 if Ticket.objects.filter(is_active=True).exists() else 1)" >/dev/null 2>&1; then
  echo "No active tickets found in SQLite, importing current dataset for local development..."
  if [ "${SEED_TICKET_LIMIT}" = "" ]; then
    ./.venv/bin/python manage.py seed_all >/dev/null
  else
    ./.venv/bin/python manage.py seed_all --max-tickets-per-file "$SEED_TICKET_LIMIT" >/dev/null
  fi
fi

BACKEND_PORT=$(find_backend_port || true)
if [ "${BACKEND_PORT}" = "" ]; then
  echo "Could not find a free local port for Django." >&2
  exit 1
fi

if is_backend_ready "$BACKEND_PORT"; then
  echo "Backend already running on ${BACKEND_HOST}:${BACKEND_PORT}, reusing existing process."
else
  ./.venv/bin/python manage.py migrate >/dev/null
  ./.venv/bin/python manage.py runserver "${BACKEND_HOST}:${BACKEND_PORT}" --noreload &
  BACKEND_PID=$!
  BACKEND_STARTED_BY_SCRIPT=1
  if ! wait_for_backend "$BACKEND_PORT"; then
    echo "Django did not become ready on ${BACKEND_HOST}:${BACKEND_PORT}." >&2
    exit 1
  fi
fi

cd "$FRONTEND_DIR"
VITE_BACKEND_ORIGIN="http://${BACKEND_HOST}:${BACKEND_PORT}" vite
