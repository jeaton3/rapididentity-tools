#!/bin/bash -x
# Connect file sync wrapper: errorlog.csv every 5min, recent-logs hourly, everything daily
# Usage: ./sync_logs.sh [destination_dir] [config_name]
# Example: ./sync_logs.sh ~/logs prod

set -e

DEST_DIR="${1:-.}"
CONFIG="${2:-prod}"
SCRIPT_DIR="${SCRIPT_DIR:-(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
PYTHON="${PYTHON:-python3}"
STATE_DIR="${DEST_DIR}/.sync_state"

# Ensure state directory exists
mkdir -p "${STATE_DIR}"

# State files to track last execution time
ERRORLOG_STATE="${STATE_DIR}/errorlog_last"
RECENT_LOGS_STATE="${STATE_DIR}/recent_logs_last"
FULL_SYNC_STATE="${STATE_DIR}/full_sync_last"

# Intervals in seconds
ERRORLOG_INTERVAL=$((5 * 60))         # 5 minutes
RECENT_LOGS_INTERVAL=$((60 * 60))     # 1 hour
FULL_SYNC_INTERVAL=$((24 * 60 * 60))  # 1 day

# Helper to check if interval has elapsed
should_run() {
    local state_file=$1
    local interval=$2
    
    if [[ ! -f "$state_file" ]]; then
        return 0  # File doesn't exist, should run
    fi
    
    local last_run=$(cat "$state_file")
    local now=$(date +%s)
    local elapsed=$((now - last_run))
    
    if [[ $elapsed -ge $interval ]]; then
        return 0  # Interval elapsed
    fi
    return 1  # Too soon
}

# Helper to update state file
mark_run() {
    local state_file=$1
    date +%s > "$state_file"
}

# Log helper
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "Starting Connect file sync (dest: $DEST_DIR, config: $CONFIG)"

# 1. Sync errorlog.csv every 5 minutes
if should_run "$ERRORLOG_STATE" "$ERRORLOG_INTERVAL"; then
    log "Syncing $CONFIG /logs/errorlog.csv ..."
    if "$PYTHON" "$SCRIPT_DIR/connect_file_utils.py" --config "$CONFIG" rsync \
        /logs/errorlog.csv "$DEST_DIR"; then
        mark_run "$ERRORLOG_STATE"
        log "✓ $CONFIG errorlog.csv sync complete"
    else
        log "✗ $CONFIG errorlog.csv sync failed"
    fi
else
    log "~ $CONFIG Skipping errorlog.csv (not yet 5 min since last run)"
fi

# 2. Sync everything with --recent-logs every hour
if should_run "$RECENT_LOGS_STATE" "$RECENT_LOGS_INTERVAL"; then
    log "Syncing $CONFIG / with --recent-logs ..."
    if "$PYTHON" "$SCRIPT_DIR/connect_file_utils.py" --config "$CONFIG" rsync \
        --recent-logs / "$DEST_DIR"; then
        mark_run "$RECENT_LOGS_STATE"
        log "✓ $CONFIG recent-logs sync complete"
    else
        log "✗ $CONFIG recent-logs sync failed"
    fi
else
    log "~ $CONFIG Skipping recent-logs sync (not yet 1 hour since last run)"
fi

# 3. Full sync everything daily
if should_run "$FULL_SYNC_STATE" "$FULL_SYNC_INTERVAL"; then
    log "$CONFIG Syncing / (full) ..."
    if "$PYTHON" "$SCRIPT_DIR/connect_file_utils.py" --config "$CONFIG" rsync \
        --exclude '2025|2026-0[12]' / "$DEST_DIR"; then
        mark_run "$FULL_SYNC_STATE"
        log "✓ $CONFIG Full sync complete"
    else
        log "✗ $CONFIG Full sync failed"
    fi
else
    log "~ Skipping $CONFIG full sync (not yet 1 day since last run)"
fi

log "Sync cycle complete"
