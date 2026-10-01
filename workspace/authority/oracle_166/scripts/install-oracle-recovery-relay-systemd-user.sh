#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
UNIT_NAME="oracle-recovery-relay.service"
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
UNIT_PATH=""
STATE_ROOT="${XDG_STATE_HOME:-$HOME/.local/state}/OracleRelay"
SOURCE_TOKEN_PATH="$ROOT/.oracle/agent-token.txt"
SOURCE_SUPERVISOR_PATH="$ROOT/scripts/Oracle-RecoveryRelaySupervisor.sh"
LEGACY_PID_PATH="$ROOT/.oracle/relay.pid"
NODE_BIN="$(command -v node || true)"
BASH_BIN="$(command -v bash || true)"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "Oracle recovery relay systemd installer requires Linux." >&2
  exit 1
fi
if [[ -z "$NODE_BIN" ]]; then
  echo "Node.js is required." >&2
  exit 1
fi
if [[ -z "$BASH_BIN" ]]; then
  echo "Bash is required." >&2
  exit 1
fi
if ! command -v git >/dev/null 2>&1; then
  echo "Git is required." >&2
  exit 1
fi
if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemd user services are required." >&2
  exit 1
fi
if [[ ! -f "$SOURCE_TOKEN_PATH" ]]; then
  echo "Missing local Oracle admin token: $SOURCE_TOKEN_PATH" >&2
  exit 1
fi
if [[ ! -f "$SOURCE_SUPERVISOR_PATH" ]]; then
  echo "Missing Linux recovery supervisor: $SOURCE_SUPERVISOR_PATH" >&2
  exit 1
fi
TOKEN_LENGTH="$(tr -d '\r\n' < "$SOURCE_TOKEN_PATH" | wc -c | tr -d ' ')"
if (( TOKEN_LENGTH < 32 )); then
  echo "The local Oracle admin token is invalid." >&2
  exit 1
fi

assert_isolated_paths() {
  local source="$1"
  local state="$2"
  case "$state/" in
    "$source/"* )
      echo "Oracle recovery state must be outside the operator checkout: $state" >&2
      return 1
      ;;
  esac
  case "$source/" in
    "$state/"* )
      echo "Oracle operator checkout must be outside the recovery state root: $source" >&2
      return 1
      ;;
  esac
}

resolve_isolated_state_root() {
  local source="$1"
  local requested="$2"
  ORACLE_RECOVERY_SOURCE_PATH="$source" \
  ORACLE_RECOVERY_STATE_REQUEST="$requested" \
  "$NODE_BIN" <<'NODE'
const fs = require("node:fs");
const path = require("node:path");
const decode = (value) => value.replace(/\\([0-7]{3})/gu, (_match, octal) => String.fromCharCode(Number.parseInt(octal, 8)));
const contains = (candidate, root) => root === "/" ? candidate.startsWith("/") : candidate === root || candidate.startsWith(`${root}/`);
const overlaps = (left, right) => left === right || left.startsWith(`${right}/`) || right.startsWith(`${left}/`);
const mountIdentity = (target) => {
  let best = null;
  for (const line of fs.readFileSync("/proc/self/mountinfo", "utf8").split(/\n/u)) {
    if (!line) continue;
    const separator = line.indexOf(" - ");
    if (separator < 0) continue;
    const fields = line.slice(0, separator).split(" ");
    if (fields.length < 5) continue;
    const majorMinor = fields[2];
    const root = decode(fields[3]);
    const mountPoint = decode(fields[4]);
    if (!contains(target, mountPoint)) continue;
    if (!best || mountPoint.length > best.mountPoint.length) best = { majorMinor, root, mountPoint };
  }
  if (!best) throw new Error(`No mountinfo entry contains ${target}`);
  const relative = path.posix.relative(best.mountPoint, target);
  return { device: best.majorMinor, internalPath: path.posix.normalize(path.posix.join(best.root, relative)) };
};
const source = fs.realpathSync(process.env.ORACLE_RECOVERY_SOURCE_PATH);
const requested = path.resolve(process.env.ORACLE_RECOVERY_STATE_REQUEST);
let ancestor = requested;
const suffix = [];
while (!fs.existsSync(ancestor)) {
  const parent = path.dirname(ancestor);
  if (parent === ancestor) throw new Error(`No existing ancestor for ${requested}`);
  suffix.unshift(path.basename(ancestor));
  ancestor = parent;
}
const ancestorPhysical = fs.realpathSync(ancestor);
const projected = path.resolve(ancestorPhysical, ...suffix);
if (overlaps(source, projected)) {
  throw new Error(`Oracle recovery source and projected state roots overlap: ${projected}`);
}
const sourceIdentity = mountIdentity(source);
const ancestorIdentity = mountIdentity(ancestorPhysical);
const projectedInternal = path.posix.normalize(path.posix.join(ancestorIdentity.internalPath, ...suffix));
if (sourceIdentity.device === ancestorIdentity.device && overlaps(sourceIdentity.internalPath, projectedInternal)) {
  throw new Error(`Oracle recovery source and projected state roots alias the same mounted filesystem subtree: ${projected}`);
}
process.stdout.write(projected);
NODE
}

assert_mount_isolation() {
  local source="$1"
  local state="$2"
  ORACLE_RECOVERY_SOURCE_MOUNT_PATH="$source" \
  ORACLE_RECOVERY_STATE_MOUNT_PATH="$state" \
  "$NODE_BIN" <<'NODE'
const fs = require("node:fs");
const path = require("node:path");
const decode = (value) => value.replace(/\\([0-7]{3})/gu, (_match, octal) => String.fromCharCode(Number.parseInt(octal, 8)));
const within = (candidate, root) => root === "/" ? candidate.startsWith("/") : candidate === root || candidate.startsWith(`${root}/`);
const identity = (input) => {
  const target = fs.realpathSync(input);
  let best = null;
  for (const line of fs.readFileSync("/proc/self/mountinfo", "utf8").split(/\n/u)) {
    if (!line) continue;
    const separator = line.indexOf(" - ");
    if (separator < 0) continue;
    const fields = line.slice(0, separator).split(" ");
    if (fields.length < 5) continue;
    const majorMinor = fields[2];
    const root = decode(fields[3]);
    const mountPoint = decode(fields[4]);
    if (!within(target, mountPoint)) continue;
    if (!best || mountPoint.length > best.mountPoint.length) best = { majorMinor, root, mountPoint };
  }
  if (!best) throw new Error(`No mountinfo entry contains ${target}`);
  const relative = path.posix.relative(best.mountPoint, target);
  return { device: best.majorMinor, internalPath: path.posix.normalize(path.posix.join(best.root, relative)) };
};
const overlaps = (left, right) => {
  if (left.device !== right.device) return false;
  const a = left.internalPath;
  const b = right.internalPath;
  return a === b || a.startsWith(`${b}/`) || b.startsWith(`${a}/`);
};
const source = identity(process.env.ORACLE_RECOVERY_SOURCE_MOUNT_PATH);
const state = identity(process.env.ORACLE_RECOVERY_STATE_MOUNT_PATH);
if (overlaps(source, state)) {
  console.error("Oracle recovery source and state roots alias the same mounted filesystem subtree.");
  process.exit(1);
}
NODE
}

assert_state_directory_isolated() {
  local state="$1"
  local candidate="$2"
  if [[ ! -d "$candidate" || -L "$candidate" ]]; then
    echo "Oracle recovery-owned directory is not a real directory: $candidate" >&2
    return 1
  fi
  local state_physical candidate_physical
  state_physical="$(cd "$state" && pwd -P)" || return 1
  candidate_physical="$(cd "$candidate" && pwd -P)" || return 1
  case "$candidate_physical/" in
    "$state_physical/"* ) ;;
    * )
      echo "Oracle recovery-owned directory escapes state root: $candidate_physical" >&2
      return 1
      ;;
  esac
  ORACLE_RECOVERY_STATE_PARENT_PATH="$state_physical" \
  ORACLE_RECOVERY_STATE_CHILD_PATH="$candidate_physical" \
  "$NODE_BIN" <<'NODE'
const fs = require("node:fs");
const path = require("node:path");
const decode = (value) => value.replace(/\\([0-7]{3})/gu, (_match, octal) => String.fromCharCode(Number.parseInt(octal, 8)));
const within = (candidate, root) => root === "/" ? candidate.startsWith("/") : candidate === root || candidate.startsWith(`${root}/`);
const identity = (input) => {
  const target = fs.realpathSync(input);
  let best = null;
  for (const line of fs.readFileSync("/proc/self/mountinfo", "utf8").split(/\n/u)) {
    if (!line) continue;
    const separator = line.indexOf(" - ");
    if (separator < 0) continue;
    const fields = line.slice(0, separator).split(" ");
    if (fields.length < 5) continue;
    const majorMinor = fields[2];
    const root = decode(fields[3]);
    const mountPoint = decode(fields[4]);
    if (!within(target, mountPoint)) continue;
    if (!best || mountPoint.length > best.mountPoint.length) best = { majorMinor, root, mountPoint };
  }
  if (!best) throw new Error(`No mountinfo entry contains ${target}`);
  const relative = path.posix.relative(best.mountPoint, target);
  return { device: best.majorMinor, internalPath: path.posix.normalize(path.posix.join(best.root, relative)) };
};
const parent = identity(process.env.ORACLE_RECOVERY_STATE_PARENT_PATH);
const child = identity(process.env.ORACLE_RECOVERY_STATE_CHILD_PATH);
const contained = child.device === parent.device && (child.internalPath === parent.internalPath || child.internalPath.startsWith(`${parent.internalPath}/`));
if (!contained) {
  console.error("Oracle recovery-owned directory is a bind/external mount outside state identity.");
  process.exit(1);
}
NODE
}

atomic_install_file() {
  local source="$1"
  local destination="$2"
  local mode="$3"
  local parent temporary
  parent="$(dirname "$destination")"
  assert_state_directory_isolated "$STATE_ROOT" "$parent" || return 1
  temporary="$(mktemp "$parent/.oracle-install.XXXXXX")" || return 1
  if ! install -m "$mode" "$source" "$temporary"; then
    rm -f -- "$temporary"
    return 1
  fi
  if ! mv -Tf -- "$temporary" "$destination"; then
    rm -f -- "$temporary"
    return 1
  fi
}

STATE_ROOT="$($NODE_BIN -e 'process.stdout.write(require("node:path").resolve(process.argv[1]))' "$STATE_ROOT")"
assert_isolated_paths "$ROOT" "$STATE_ROOT"
STATE_ROOT="$(resolve_isolated_state_root "$ROOT" "$STATE_ROOT")"
assert_isolated_paths "$ROOT" "$STATE_ROOT"
mkdir -p "$STATE_ROOT"
STATE_ROOT="$(cd "$STATE_ROOT" && pwd -P)"
assert_isolated_paths "$ROOT" "$STATE_ROOT"
assert_mount_isolation "$ROOT" "$STATE_ROOT"
chmod 700 "$STATE_ROOT"

UNIT_DIR="$($NODE_BIN -e 'process.stdout.write(require("node:path").resolve(process.argv[1]))' "$UNIT_DIR")"
UNIT_DIR="$(resolve_isolated_state_root "$ROOT" "$UNIT_DIR")"
mkdir -p "$UNIT_DIR"
UNIT_DIR="$(cd "$UNIT_DIR" && pwd -P)"
assert_isolated_paths "$ROOT" "$UNIT_DIR"
assert_mount_isolation "$ROOT" "$UNIT_DIR"
UNIT_PATH="$UNIT_DIR/$UNIT_NAME"

BOOTSTRAP_ROOT="$STATE_ROOT/bootstrap-source"
BOOTSTRAP_SCRIPTS="$BOOTSTRAP_ROOT/scripts"
BOOTSTRAP_STATE="$BOOTSTRAP_ROOT/.oracle"
RUNTIME_REPO="$STATE_ROOT/repo"
LOCAL_TOKEN_PATH="$BOOTSTRAP_STATE/agent-token.txt"
SUPERVISOR_PATH="$BOOTSTRAP_SCRIPTS/Oracle-RecoveryRelaySupervisor.sh"

for RECOVERY_DIR in "$BOOTSTRAP_ROOT" "$BOOTSTRAP_SCRIPTS" "$BOOTSTRAP_STATE"; do
  if [[ -e "$RECOVERY_DIR" || -L "$RECOVERY_DIR" ]]; then
    assert_state_directory_isolated "$STATE_ROOT" "$RECOVERY_DIR"
  fi
done
mkdir -p "$BOOTSTRAP_SCRIPTS" "$BOOTSTRAP_STATE"
for RECOVERY_DIR in "$BOOTSTRAP_ROOT" "$BOOTSTRAP_SCRIPTS" "$BOOTSTRAP_STATE"; do
  assert_state_directory_isolated "$STATE_ROOT" "$RECOVERY_DIR"
done
chmod 700 "$BOOTSTRAP_ROOT" "$BOOTSTRAP_SCRIPTS" "$BOOTSTRAP_STATE"
atomic_install_file "$SOURCE_SUPERVISOR_PATH" "$SUPERVISOR_PATH" 700
atomic_install_file "$SOURCE_TOKEN_PATH" "$LOCAL_TOKEN_PATH" 600

if [[ -f "$LEGACY_PID_PATH" ]]; then
  LEGACY_PID="$(cat "$LEGACY_PID_PATH" 2>/dev/null || true)"
  if [[ "$LEGACY_PID" =~ ^[0-9]+$ ]] && kill -0 "$LEGACY_PID" 2>/dev/null; then
    kill "$LEGACY_PID" 2>/dev/null || true
    for _ in {1..30}; do
      if ! kill -0 "$LEGACY_PID" 2>/dev/null; then break; fi
      sleep 0.2
    done
    if kill -0 "$LEGACY_PID" 2>/dev/null; then
      echo "Existing manual Oracle relay did not stop cleanly; refusing a duplicate relay." >&2
      exit 1
    fi
  fi
  rm -f "$LEGACY_PID_PATH"
fi

UNIT_TEMP="$(mktemp "$UNIT_DIR/.oracle-recovery-relay-unit.XXXXXX")"
cat > "$UNIT_TEMP" <<EOF
[Unit]
Description=Oracle Recovery Relay (fallback only)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory="$STATE_ROOT"
Environment="ORACLE_RECOVERY_SOURCE_ROOT=$ROOT"
Environment="ORACLE_RECOVERY_STATE_ROOT=$STATE_ROOT"
Environment="ORACLE_RECOVERY_TOKEN_PATH=$LOCAL_TOKEN_PATH"
Environment="ORACLE_RECOVERY_NODE_BIN=$NODE_BIN"
Environment="ORACLE_RECOVERY_RESTART_DELAY_SECONDS=15"
Environment="ORACLE_RELAY_DURATION_MINUTES=0"
Environment="ORACLE_RELAY_POLL_SECONDS=3"
Environment="ORACLE_RELAY_MAX_CONCURRENCY=4"
Environment="ORACLE_TERMINAL_ROOTS=$HOME:$ROOT:$RUNTIME_REPO"
ExecStart="$BASH_BIN" "$SUPERVISOR_PATH"
Restart=always
RestartSec=15s
TimeoutStopSec=30s

[Install]
WantedBy=default.target
EOF
chmod 600 "$UNIT_TEMP"
mv -Tf -- "$UNIT_TEMP" "$UNIT_PATH"

systemctl --user daemon-reload
systemctl --user enable "$UNIT_NAME"
systemctl --user restart "$UNIT_NAME"

LINGER="unknown"
if command -v loginctl >/dev/null 2>&1; then
  LINGER="$(loginctl show-user "$USER" -p Linger --value 2>/dev/null || true)"
fi

STATE="$(systemctl --user is-active "$UNIT_NAME" 2>/dev/null || true)"
ENABLED="$(systemctl --user is-enabled "$UNIT_NAME" 2>/dev/null || true)"
json_string() {
  "$NODE_BIN" -e 'process.stdout.write(JSON.stringify(process.argv[1]))' "$1"
}
printf '{\n'
printf '  "schemaVersion": "oracle.recovery-relay-install.v1",\n'
printf '  "ok": %s,\n' "$([[ "$STATE" == "active" ]] && echo true || echo false)"
printf '  "service": "%s",\n' "$UNIT_NAME"
printf '  "state": "%s",\n' "$STATE"
printf '  "enabled": "%s",\n' "$ENABLED"
printf '  "linger": "%s",\n' "$LINGER"
printf '  "sourceRoot": %s,\n' "$(json_string "$ROOT")"
printf '  "stateRoot": %s,\n' "$(json_string "$STATE_ROOT")"
printf '  "runtimeRepo": %s,\n' "$(json_string "$RUNTIME_REPO")"
printf '  "tokenLocal": true,\n'
printf '  "tokenExposed": false,\n'
printf '  "indefiniteRelay": true,\n'
printf '  "isolatedRuntime": true,\n'
printf '  "primaryInteractiveTransport": "oracle.live.v1",\n'
printf '  "recoveryTransport": "github-relay-fallback"\n'
printf '}\n'

if [[ "$LINGER" != "yes" ]]; then
  echo "WARNING: user lingering is not enabled; the recovery relay will not survive logout/reboot until 'loginctl enable-linger $USER' is configured." >&2
fi
if [[ "$STATE" != "active" ]]; then
  exit 1
fi
