#!/usr/bin/env bash
set -uo pipefail

SOURCE_ROOT_INPUT="${ORACLE_RECOVERY_SOURCE_ROOT:?ORACLE_RECOVERY_SOURCE_ROOT is required}"
STATE_ROOT_INPUT="${ORACLE_RECOVERY_STATE_ROOT:-${XDG_STATE_HOME:-$HOME/.local/state}/OracleRelay}"
NODE_BIN="${ORACLE_RECOVERY_NODE_BIN:-$(command -v node || true)}"
RESTART_DELAY_SECONDS="${ORACLE_RECOVERY_RESTART_DELAY_SECONDS:-15}"
EXPECTED_REMOTE="https://github.com/jaydumisuni/Oracle-.git"
RUNTIME_GIT_USER_NAME="Oracle Relay"
RUNTIME_GIT_USER_EMAIL="oracle-relay@users.noreply.github.com"

if [[ -z "$NODE_BIN" ]]; then
  echo "Node.js is required." >&2
  exit 1
fi
if ! command -v git >/dev/null 2>&1; then
  echo "Git is required." >&2
  exit 1
fi
if [[ ! "$RESTART_DELAY_SECONDS" =~ ^[0-9]+$ ]] || (( RESTART_DELAY_SECONDS < 5 || RESTART_DELAY_SECONDS > 300 )); then
  echo "ORACLE_RECOVERY_RESTART_DELAY_SECONDS must be between 5 and 300." >&2
  exit 1
fi

physical_dir() {
  local path="$1"
  (cd -- "$path" 2>/dev/null && pwd -P)
}

paths_overlap() {
  local first="$1"
  local second="$2"
  [[ "$first" == "$second" || "$first" == "$second/"* || "$second" == "$first/"* ]]
}

# Resolve a not-yet-created state path through its nearest existing ancestor and
# compare the projected Linux mount identity with the source before mkdir. This
# prevents a symlink or bind-mounted parent from causing refusal only after the
# operator checkout has already been mutated by directory creation.
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

# Resolve an existing path to its underlying Linux mount identity rather than
# relying only on pwd -P. Bind mounts preserve a different visible pathname
# while mapping to the same filesystem-internal subtree.
mount_identity() {
  local target="$1"
  ORACLE_MOUNT_IDENTITY_PATH="$target" "$NODE_BIN" <<'NODE'
const fs = require("node:fs");
const path = require("node:path");
const target = fs.realpathSync(process.env.ORACLE_MOUNT_IDENTITY_PATH);
const decode = (value) => value.replace(/\\([0-7]{3})/gu, (_match, octal) => String.fromCharCode(Number.parseInt(octal, 8)));
const within = (candidate, root) => root === "/" ? candidate.startsWith("/") : candidate === root || candidate.startsWith(`${root}/`);
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
const internalPath = path.posix.normalize(path.posix.join(best.root, relative));
process.stdout.write(`${best.majorMinor}\t${internalPath}`);
NODE
}

mount_identities_overlap() {
  local first_identity="$1"
  local second_identity="$2"
  local first_device first_path second_device second_path
  IFS=$'\t' read -r first_device first_path <<< "$first_identity"
  IFS=$'\t' read -r second_device second_path <<< "$second_identity"
  [[ -n "$first_device" && -n "$first_path" && -n "$second_device" && -n "$second_path" ]] || return 2
  [[ "$first_device" == "$second_device" ]] || return 1
  paths_overlap "$first_path" "$second_path"
}

mount_identity_within() {
  local child_identity="$1"
  local parent_identity="$2"
  local child_device child_path parent_device parent_path
  IFS=$'\t' read -r child_device child_path <<< "$child_identity"
  IFS=$'\t' read -r parent_device parent_path <<< "$parent_identity"
  [[ -n "$child_device" && -n "$child_path" && -n "$parent_device" && -n "$parent_path" ]] || return 2
  [[ "$child_device" == "$parent_device" ]] || return 1
  [[ "$child_path" == "$parent_path" || "$child_path" == "$parent_path/"* ]]
}

is_mountpoint_path() {
  local target="$1"
  ORACLE_MOUNTPOINT_PATH="$target" "$NODE_BIN" <<'NODE'
const fs = require("node:fs");
const target = fs.realpathSync(process.env.ORACLE_MOUNTPOINT_PATH);
const decode = (value) => value.replace(/\\([0-7]{3})/gu, (_match, octal) => String.fromCharCode(Number.parseInt(octal, 8)));
for (const line of fs.readFileSync("/proc/self/mountinfo", "utf8").split(/\n/u)) {
  if (!line) continue;
  const separator = line.indexOf(" - ");
  if (separator < 0) continue;
  const fields = line.slice(0, separator).split(" ");
  if (fields.length >= 5 && decode(fields[4]) === target) process.exit(0);
}
process.exit(1);
NODE
}

nested_mount_count() {
  local target="$1"
  ORACLE_NESTED_MOUNT_ROOT="$target" "$NODE_BIN" <<'NODE'
const fs = require("node:fs");
const target = fs.realpathSync(process.env.ORACLE_NESTED_MOUNT_ROOT).replace(/\/+$/u, "") || "/";
const decode = (value) => value.replace(/\\([0-7]{3})/gu, (_match, octal) => String.fromCharCode(Number.parseInt(octal, 8)));
let count = 0;
for (const line of fs.readFileSync("/proc/self/mountinfo", "utf8").split(/\n/u)) {
  if (!line) continue;
  const separator = line.indexOf(" - ");
  if (separator < 0) continue;
  const fields = line.slice(0, separator).split(" ");
  if (fields.length < 5) continue;
  const mountPoint = decode(fields[4]);
  if (target === "/" ? mountPoint !== "/" : mountPoint.startsWith(`${target}/`)) count += 1;
}
process.stdout.write(String(count));
NODE
}

# Treat the dedicated runtime's local Git configuration as data, not executable
# authority. Read only the physical .git/config with includes disabled and
# accept only keys emitted by Oracle's clone/bootstrap contract. This rejects
# include/includeIf indirection, filter.* clean/smudge/process commands, custom
# helpers, URL rewrites and other repository-local execution/config injection
# before status/fetch/reset can touch the worktree.
runtime_local_config_safe() {
  local config="$RUNTIME_REPO/.git/config"
  [[ -f "$config" && ! -L "$config" ]] || return 1
  [[ "$(stat -c '%h' "$config" 2>/dev/null || true)" == "1" ]] || return 1

  local keys key lower raw_url raw_fetch raw_bare branch_remote branch_merge
  keys="$(git config --file "$config" --no-includes --name-only --list 2>/dev/null)" || return 1
  while IFS= read -r key; do
    [[ -n "$key" ]] || continue
    lower="${key,,}"
    case "$lower" in
      core.repositoryformatversion|core.filemode|core.bare|core.logallrefupdates|core.hookspath|core.fsmonitor|remote.origin.url|remote.origin.fetch|remote.origin.promisor|remote.origin.partialclonefilter|branch.main.remote|branch.main.merge|user.name|user.email|commit.gpgsign)
        ;;
      *)
        return 1
        ;;
    esac
  done <<< "$keys"

  raw_url="$(git config --file "$config" --no-includes --get remote.origin.url 2>/dev/null || true)"
  raw_fetch="$(git config --file "$config" --no-includes --get remote.origin.fetch 2>/dev/null || true)"
  raw_bare="$(git config --file "$config" --no-includes --get core.bare 2>/dev/null || true)"
  branch_remote="$(git config --file "$config" --no-includes --get branch.main.remote 2>/dev/null || true)"
  branch_merge="$(git config --file "$config" --no-includes --get branch.main.merge 2>/dev/null || true)"
  [[ "$raw_url" == "$EXPECTED_REMOTE" ]] || return 1
  [[ "$raw_fetch" == "+refs/heads/main:refs/remotes/origin/main" ]] || return 1
  [[ "$raw_bare" == "false" ]] || return 1
  [[ "$branch_remote" == "origin" ]] || return 1
  [[ "$branch_merge" == "refs/heads/main" ]] || return 1
  return 0
}

SOURCE_ROOT="$(physical_dir "$SOURCE_ROOT_INPUT")" || {
  echo "Oracle recovery source root is unavailable: $SOURCE_ROOT_INPUT" >&2
  exit 1
}
STATE_ROOT_CANDIDATE="$(resolve_isolated_state_root "$SOURCE_ROOT" "$STATE_ROOT_INPUT")" || {
  echo "Oracle recovery state root failed pre-mutation isolation validation: $STATE_ROOT_INPUT" >&2
  exit 1
}
mkdir -p "$STATE_ROOT_CANDIDATE"
STATE_ROOT="$(physical_dir "$STATE_ROOT_CANDIDATE")" || {
  echo "Oracle recovery state root is unavailable: $STATE_ROOT_CANDIDATE" >&2
  exit 1
}
if paths_overlap "$SOURCE_ROOT" "$STATE_ROOT"; then
  echo "Oracle recovery source and state roots must remain physically isolated." >&2
  exit 1
fi
SOURCE_MOUNT_IDENTITY="$(mount_identity "$SOURCE_ROOT")" || {
  echo "Oracle could not resolve source mount identity." >&2
  exit 1
}
STATE_MOUNT_IDENTITY="$(mount_identity "$STATE_ROOT")" || {
  echo "Oracle could not resolve recovery-state mount identity." >&2
  exit 1
}
mount_identities_overlap "$SOURCE_MOUNT_IDENTITY" "$STATE_MOUNT_IDENTITY"
mount_overlap_rc=$?
if (( mount_overlap_rc == 0 )); then
  echo "Oracle recovery source and state roots alias the same mounted filesystem subtree." >&2
  exit 1
fi
if (( mount_overlap_rc != 1 )); then
  echo "Oracle could not validate source/state mount isolation." >&2
  exit 1
fi

RUNTIME_REPO="$STATE_ROOT/repo"
RUNTIME_QUARANTINE="$STATE_ROOT/quarantine"
STATUS_PATH="$STATE_ROOT/recovery-supervisor-status.json"
LOCAL_TOKEN_PATH="${ORACLE_RECOVERY_TOKEN_PATH:-$STATE_ROOT/bootstrap-source/.oracle/agent-token.txt}"

state_directory_isolated() {
  local candidate="$1"
  [[ -d "$candidate" && ! -L "$candidate" ]] || return 1
  local physical child_identity
  physical="$(physical_dir "$candidate")" || return 1
  [[ "$physical" == "$STATE_ROOT" || "$physical" == "$STATE_ROOT/"* ]] || return 1
  child_identity="$(mount_identity "$candidate")" || return 1
  mount_identity_within "$child_identity" "$STATE_MOUNT_IDENTITY"
}

runtime_directory_isolated() {
  local candidate="$1"
  [[ -d "$candidate" && ! -L "$candidate" ]] || return 1
  local runtime_physical candidate_physical runtime_identity candidate_identity
  runtime_physical="$(physical_dir "$RUNTIME_REPO")" || return 1
  candidate_physical="$(physical_dir "$candidate")" || return 1
  [[ "$candidate_physical" == "$runtime_physical" || "$candidate_physical" == "$runtime_physical/"* ]] || return 1
  runtime_identity="$(mount_identity "$RUNTIME_REPO")" || return 1
  candidate_identity="$(mount_identity "$candidate")" || return 1
  mount_identity_within "$candidate_identity" "$runtime_identity"
}

chmod 700 "$STATE_ROOT"
TOKEN_PARENT="$(dirname "$LOCAL_TOKEN_PATH")"
if [[ ! -f "$LOCAL_TOKEN_PATH" || -L "$LOCAL_TOKEN_PATH" ]] || ! state_directory_isolated "$TOKEN_PARENT"; then
  echo "Missing or non-isolated local Oracle recovery token: $LOCAL_TOKEN_PATH" >&2
  exit 1
fi
chmod 600 "$LOCAL_TOKEN_PATH"

write_status() {
  local state="$1"
  local detail="${2:-}"
  local relay_exit="${3:-}"
  local temporary
  temporary="$(mktemp "$STATE_ROOT/.oracle-supervisor-status.XXXXXX")" || return 1
  if ! ORACLE_STATUS_PATH="$temporary" \
    ORACLE_STATUS_STATE="$state" \
    ORACLE_STATUS_DETAIL="$detail" \
    ORACLE_STATUS_SOURCE_ROOT="$SOURCE_ROOT" \
    ORACLE_STATUS_RUNTIME_REPO="$RUNTIME_REPO" \
    ORACLE_STATUS_RELAY_EXIT="$relay_exit" \
    "$NODE_BIN" -e '
      const fs = require("node:fs");
      const path = process.env.ORACLE_STATUS_PATH;
      const rawExit = process.env.ORACLE_STATUS_RELAY_EXIT || "";
      const body = {
        schemaVersion: "oracle.recovery-relay-supervisor.v1",
        state: process.env.ORACLE_STATUS_STATE,
        detail: process.env.ORACLE_STATUS_DETAIL || "",
        host: require("node:os").hostname(),
        supervisorProcessId: Number(process.env.ORACLE_SUPERVISOR_PID || 0) || null,
        relayExitCode: /^-?\d+$/.test(rawExit) ? Number(rawExit) : null,
        sourceRoot: process.env.ORACLE_STATUS_SOURCE_ROOT,
        runtimeRepo: process.env.ORACLE_STATUS_RUNTIME_REPO,
        tokenExposed: false,
        updatedAt: new Date().toISOString(),
      };
      fs.writeFileSync(path, JSON.stringify(body, null, 2) + "\n", { mode: 0o600 });
    '; then
    rm -f -- "$temporary"
    return 1
  fi
  chmod 600 "$temporary" || { rm -f -- "$temporary"; return 1; }
  if ! mv -Tf -- "$temporary" "$STATUS_PATH"; then
    rm -f -- "$temporary"
    return 1
  fi
}

runtime_isolated() {
  [[ -e "$RUNTIME_REPO" || -L "$RUNTIME_REPO" ]] || return 1
  [[ ! -L "$RUNTIME_REPO" ]] || return 1

  local physical runtime_mount_identity state_mount_identity source_mount_identity overlap_rc nested_count
  physical="$(physical_dir "$RUNTIME_REPO")" || return 1
  [[ "$physical" != "$STATE_ROOT" ]] || return 1
  [[ "$physical" == "$STATE_ROOT/"* ]] || return 1
  paths_overlap "$physical" "$SOURCE_ROOT" && return 1
  nested_count="$(nested_mount_count "$RUNTIME_REPO")" || return 1
  [[ "$nested_count" =~ ^[0-9]+$ ]] || return 1
  (( nested_count == 0 )) || return 1
  runtime_mount_identity="$(mount_identity "$RUNTIME_REPO")" || return 1
  state_mount_identity="$(mount_identity "$STATE_ROOT")" || return 1
  source_mount_identity="$(mount_identity "$SOURCE_ROOT")" || return 1
  mount_identity_within "$runtime_mount_identity" "$state_mount_identity" || return 1
  mount_identities_overlap "$runtime_mount_identity" "$source_mount_identity"
  overlap_rc=$?
  if (( overlap_rc == 0 )); then return 1; fi
  (( overlap_rc == 1 )) || return 1
  return 0
}

runtime_valid() {
  runtime_isolated || return 1
  [[ -d "$RUNTIME_REPO/.git" ]] || return 1
  [[ ! -L "$RUNTIME_REPO/.git" ]] || return 1
  runtime_local_config_safe || return 1

  local inside remote runtime_physical git_physical top_physical common_physical git_dir top_level common_dir common_candidate rewrites pushurl
  inside="$(git -C "$RUNTIME_REPO" rev-parse --is-inside-work-tree 2>/dev/null || true)"
  [[ "$inside" == "true" ]] || return 1

  runtime_physical="$(physical_dir "$RUNTIME_REPO")" || return 1
  top_level="$(git -C "$RUNTIME_REPO" rev-parse --show-toplevel 2>/dev/null || true)"
  git_dir="$(git -C "$RUNTIME_REPO" rev-parse --absolute-git-dir 2>/dev/null || true)"
  common_dir="$(git -C "$RUNTIME_REPO" rev-parse --git-common-dir 2>/dev/null || true)"
  [[ -n "$top_level" && -n "$git_dir" && -n "$common_dir" ]] || return 1
  top_physical="$(physical_dir "$top_level")" || return 1
  git_physical="$(physical_dir "$git_dir")" || return 1
  if [[ "$common_dir" == /* ]]; then common_candidate="$common_dir"; else common_candidate="$RUNTIME_REPO/$common_dir"; fi
  common_physical="$(physical_dir "$common_candidate")" || return 1
  [[ "$top_physical" == "$runtime_physical" ]] || return 1
  [[ "$git_physical" == "$runtime_physical/.git" ]] || return 1
  [[ "$common_physical" == "$runtime_physical/.git" ]] || return 1

  remote="$(git -C "$RUNTIME_REPO" remote get-url origin 2>/dev/null || true)"
  [[ "$remote" == "$EXPECTED_REMOTE" ]] || return 1
  pushurl="$(git -C "$RUNTIME_REPO" config --local --get-all remote.origin.pushurl 2>/dev/null || true)"
  [[ -z "$pushurl" ]] || return 1
  rewrites="$(git -C "$RUNTIME_REPO" config --local --get-regexp '^url\..*\.(insteadOf|pushInsteadOf)$' 2>/dev/null || true)"
  [[ -z "$rewrites" ]]
}

quarantine_runtime() {
  [[ -e "$RUNTIME_REPO" || -L "$RUNTIME_REPO" ]] || return 0
  if [[ -e "$RUNTIME_QUARANTINE" || -L "$RUNTIME_QUARANTINE" ]]; then
    if ! state_directory_isolated "$RUNTIME_QUARANTINE"; then
      write_status "quarantine-rejected" "Recovery quarantine path is not an isolated state-owned directory; refusing to move runtime evidence."
      return 1
    fi
  else
    mkdir -p "$RUNTIME_QUARANTINE" || return 1
    state_directory_isolated "$RUNTIME_QUARANTINE" || return 1
  fi

  local stamp destination
  stamp="$(date -u +%Y%m%d-%H%M%S)"
  destination="$RUNTIME_QUARANTINE/repo-$stamp"
  if [[ -e "$destination" || -L "$destination" ]]; then
    destination="$destination-$$"
  fi

  if [[ ! -L "$RUNTIME_REPO" ]] && is_mountpoint_path "$RUNTIME_REPO"; then
    write_status "runtime-rejected-mount" "Invalid recovery runtime is a mount point; preserving it in place without touching its mounted target."
    return 1
  fi

  local nested_count
  if [[ ! -L "$RUNTIME_REPO" ]]; then
    nested_count="$(nested_mount_count "$RUNTIME_REPO")" || return 1
    [[ "$nested_count" =~ ^[0-9]+$ ]] || return 1
    if (( nested_count > 0 )); then
      write_status "runtime-rejected-nested-mount" "Invalid recovery runtime contains nested mount points; preserving it in place without touching mounted targets."
      return 1
    fi
  fi

  mv -- "$RUNTIME_REPO" "$destination" || return 1
  write_status "runtime-quarantined" "Invalid or non-isolated recovery runtime preserved at $destination."
}

clone_runtime() {
  write_status "cloning" "Creating isolated Oracle recovery runtime."
  git -c gc.auto=0 clone --filter=blob:none --single-branch --branch main "$EXPECTED_REMOTE" "$RUNTIME_REPO"
  runtime_isolated || return 1
}

configure_runtime_identity() {
  runtime_valid || return 1
  local hooks_dir="$RUNTIME_REPO/.git/oracle-disabled-hooks"
  rm -rf -- "$hooks_dir"
  mkdir -p "$hooks_dir"
  chmod 700 "$hooks_dir"

  git -C "$RUNTIME_REPO" config --local user.name "$RUNTIME_GIT_USER_NAME" || return 1
  git -C "$RUNTIME_REPO" config --local user.email "$RUNTIME_GIT_USER_EMAIL" || return 1
  git -C "$RUNTIME_REPO" config --local commit.gpgsign false || return 1
  git -C "$RUNTIME_REPO" config --local core.hooksPath "$hooks_dir" || return 1
  git -C "$RUNTIME_REPO" config --local core.fsmonitor false || return 1
  git -C "$RUNTIME_REPO" config --local --unset-all credential.helper >/dev/null 2>&1 || true

  [[ "$(git -C "$RUNTIME_REPO" config --local --get user.name 2>/dev/null || true)" == "$RUNTIME_GIT_USER_NAME" ]] || return 1
  [[ "$(git -C "$RUNTIME_REPO" config --local --get user.email 2>/dev/null || true)" == "$RUNTIME_GIT_USER_EMAIL" ]] || return 1
  [[ "$(git -C "$RUNTIME_REPO" config --local --get commit.gpgsign 2>/dev/null || true)" == "false" ]] || return 1
  [[ "$(git -C "$RUNTIME_REPO" config --local --get core.hooksPath 2>/dev/null || true)" == "$hooks_dir" ]] || return 1
  [[ "$(git -C "$RUNTIME_REPO" config --local --get core.fsmonitor 2>/dev/null || true)" == "false" ]] || return 1
  [[ -z "$(git -C "$RUNTIME_REPO" config --local --get-all credential.helper 2>/dev/null || true)" ]]
}

copy_runtime_token() {
  runtime_isolated || return 1
  local runtime_oracle="$RUNTIME_REPO/.oracle"
  if [[ -e "$runtime_oracle" || -L "$runtime_oracle" ]]; then
    runtime_directory_isolated "$runtime_oracle" || return 1
  else
    mkdir -p "$runtime_oracle" || return 1
    runtime_directory_isolated "$runtime_oracle" || return 1
  fi
  chmod 700 "$runtime_oracle"

  local temporary="$runtime_oracle/.agent-token.XXXXXX"
  temporary="$(mktemp "$temporary")" || return 1
  if ! install -m 600 "$LOCAL_TOKEN_PATH" "$temporary"; then
    rm -f -- "$temporary"
    return 1
  fi
  if ! mv -Tf -- "$temporary" "$runtime_oracle/agent-token.txt"; then
    rm -f -- "$temporary"
    return 1
  fi
}

prepare_runtime() {
  if [[ -e "$RUNTIME_REPO" || -L "$RUNTIME_REPO" ]] && ! runtime_valid; then
    quarantine_runtime || return 1
  fi
  if [[ ! -e "$RUNTIME_REPO" && ! -L "$RUNTIME_REPO" ]]; then
    clone_runtime || return 1
  fi
  runtime_valid || return 1
  configure_runtime_identity || return 1

  local dirty
  dirty="$(git -C "$RUNTIME_REPO" status --porcelain --untracked-files=normal 2>/dev/null || true)"
  if [[ -z "$dirty" ]]; then
    git -c core.commitGraph=false -C "$RUNTIME_REPO" fetch --no-write-commit-graph --no-auto-maintenance origin main || return 1
    runtime_isolated || return 1
    runtime_valid || return 1
    git -c core.commitGraph=false -C "$RUNTIME_REPO" reset --hard origin/main || return 1
  else
    write_status "runtime-recovery" "Isolated runtime has pending Git state; preserving it for canonical relay recovery."
  fi

  copy_runtime_token || return 1
  runtime_valid || return 1
  [[ -f "$RUNTIME_REPO/scripts/start-oracle-private-relay.mjs" ]] || return 1
  [[ -f "$RUNTIME_REPO/scripts/run-oracle-linux-control.mjs" ]] || return 1
  return 0
}

relay_failed_on_unrelated_runtime_state() {
  local relay_status="$RUNTIME_REPO/.oracle/relay-status.json"
  [[ -f "$relay_status" && ! -L "$relay_status" ]] || return 1
  ORACLE_RELAY_STATUS_PATH="$relay_status" "$NODE_BIN" -e '
    const fs = require("node:fs");
    const p = process.env.ORACLE_RELAY_STATUS_PATH;
    try {
      const v = JSON.parse(fs.readFileSync(p, "utf8"));
      const detail = String(v?.detail || "");
      process.exit(v?.state === "failed" && detail.includes("refusing automatic recovery because unrelated files are present") ? 0 : 1);
    } catch {
      process.exit(1);
    }
  '
}

run_relay() {
  runtime_valid || {
    write_status "runtime-invalid" "Recovery runtime failed physical/mount/Git-metadata containment or repository validation before launch."
    return 1
  }
  export ORACLE_REPO_ROOT="$RUNTIME_REPO"
  export ORACLE_RELAY_DURATION_MINUTES="0"
  export ORACLE_RELAY_POLL_SECONDS="${ORACLE_RELAY_POLL_SECONDS:-3}"
  export ORACLE_RELAY_MAX_CONCURRENCY="${ORACLE_RELAY_MAX_CONCURRENCY:-4}"

  local existing_roots="${ORACLE_TERMINAL_ROOTS:-}"
  local required_roots="$HOME:$SOURCE_ROOT:$RUNTIME_REPO"
  if [[ -n "$existing_roots" ]]; then
    export ORACLE_TERMINAL_ROOTS="$required_roots:$existing_roots"
  else
    export ORACLE_TERMINAL_ROOTS="$required_roots"
  fi

  write_status "running" "Recovery-only relay is active from isolated runtime."
  (
    cd "$RUNTIME_REPO" || exit 1
    "$NODE_BIN" "$RUNTIME_REPO/scripts/start-oracle-private-relay.mjs"
  )
}

export ORACLE_SUPERVISOR_PID="$$"
write_status "starting" "Linux recovery relay supervisor starting."

while true; do
  if ! prepare_runtime; then
    write_status "prepare-failed" "Isolated recovery runtime preparation failed."
    sleep "$RESTART_DELAY_SECONDS"
    continue
  fi

  run_relay
  relay_exit=$?
  write_status "relay-exited" "Recovery relay exited; supervisor will refresh and restart it." "$relay_exit"

  if (( relay_exit != 0 )) && relay_failed_on_unrelated_runtime_state; then
    quarantine_runtime || true
  fi

  sleep "$RESTART_DELAY_SECONDS"
done
