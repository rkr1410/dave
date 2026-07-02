#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[dave-install] %s\n' "$*"
}

die() {
  printf '[dave-install] error: %s\n' "$*" >&2
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

[[ "$#" -eq 0 ]] || die "install.sh does not take arguments"

REPO_ROOT="$(script_dir)"
BIN_DIR="$HOME/bin"
VENV_DIR="$REPO_ROOT/.venv"
WRAPPER="$BIN_DIR/dave"

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  log "creating virtualenv: $VENV_DIR"
  python3 -m venv "$VENV_DIR"
else
  log "virtualenv already exists: $VENV_DIR"
fi

VENV_PYTHON="$VENV_DIR/bin/python"

log "upgrading pip"
"$VENV_PYTHON" -m pip install --upgrade pip

log "installing package"
"$VENV_PYTHON" -m pip install -e "$REPO_ROOT"

mkdir -p "$BIN_DIR"

if ! is_known_dave_wrapper "$WRAPPER"; then
  die "refusing to overwrite non-managed wrapper: $WRAPPER"
fi

TMP_WRAPPER="$WRAPPER.tmp.$$"
{
  printf '#!/usr/bin/env bash\n'
  printf '# managed-by: dave/install.sh\n'
  printf '# source: %s\n' "$REPO_ROOT"
  printf '# venv: %s\n' "$VENV_DIR"
  printf 'exec %q "$@"\n' "$VENV_DIR/bin/dave"
} > "$TMP_WRAPPER"
chmod +x "$TMP_WRAPPER"
mv "$TMP_WRAPPER" "$WRAPPER"

log "installed wrapper: $WRAPPER"

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *) log "warning: $BIN_DIR is not on PATH for this shell" ;;
esac

log "done; run: dave"
