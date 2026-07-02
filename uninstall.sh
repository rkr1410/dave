#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[dave-uninstall] %s\n' "$*"
}

die() {
  printf '[dave-uninstall] error: %s\n' "$*" >&2
  exit 1
}

script_dir() {
  local source_dir
  source_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  printf '%s\n' "$source_dir"
}

is_known_dave_wrapper() {
  local wrapper="$1"
  [[ ! -e "$wrapper" ]] && return 0
  [[ -f "$wrapper" ]] || return 1
  grep -Fq 'managed-by: dave/install.sh' "$wrapper" && return 0
  grep -Fq "exec $REPO_ROOT/.venv/bin/dave" "$wrapper" && return 0
  return 1
}

[[ "$#" -eq 0 ]] || die "uninstall.sh does not take arguments"

REPO_ROOT="$(script_dir)"
BIN_DIR="$HOME/bin"
VENV_DIR="$REPO_ROOT/.venv"
WRAPPER="$BIN_DIR/dave"

if [[ -e "$WRAPPER" ]]; then
  if is_known_dave_wrapper "$WRAPPER"; then
    log "removing wrapper: $WRAPPER"
    rm -f "$WRAPPER"
  else
    die "refusing to remove non-managed wrapper: $WRAPPER"
  fi
else
  log "wrapper already absent: $WRAPPER"
fi

if [[ -d "$VENV_DIR" ]]; then
  log "removing virtualenv: $VENV_DIR"
  rm -rf "$VENV_DIR"
else
  log "virtualenv already absent: $VENV_DIR"
fi

log "done"
