#!/usr/bin/env bash
# Networked source/dependency installation only. Never starts a paid model call.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="${1:-$ROOT/.native}"
PYTHON="${PYTHON:-python3.13}"
mkdir -p "$WORK"
checkout() {
  local name="$1" repo="$2" pin="$3"
  if [ ! -d "$WORK/$name/.git" ]; then
    git clone --no-checkout "https://github.com/$repo.git" "$WORK/$name"
  else
    test -z "$(git -C "$WORK/$name" status --porcelain)" || { echo "Refusing dirty source: $name" >&2; exit 2; }
  fi
  git -C "$WORK/$name" fetch origin "$pin"
  git -C "$WORK/$name" checkout --detach "$pin"
  test "$(git -C "$WORK/$name" rev-parse HEAD)" = "$pin"
}
checkout rcc effacermonexistence/rcc-revas-veritas-benchmark 805cd5ff17e431cf50a3dafa7f78a60a704613b9
checkout veritas veritasfuji-japan/veritas_os b39961b003179aea70e320a57cb000f56a81951e
checkout agentdojo ethz-spylab/agentdojo a75aba7631d3ca5fb7ab938965c97ead2f9ff84b
checkout tau sierra-research/tau-bench 59a200c6d575d595120f1cb70fea53cef0632f6b
checkout tau2 sierra-research/tau2-bench b7ea9074c1cba482b30687fecdb5c8425fd6f619
"$PYTHON" -m venv "$WORK/venv"
# CPU index supplies the observed +cpu build; the base version spec accepts it.
"$WORK/venv/bin/python" -m pip install --index-url https://download.pytorch.org/whl/cpu 'torch==2.10.0'
"$WORK/venv/bin/python" -m pip install -r "$ROOT/requirements-native.txt"
"$WORK/venv/bin/python" -m pip install --no-deps "$ROOT"
"$WORK/venv/bin/python" "$ROOT/scripts/check_native_dependencies.py"
printf '\nRun exact native validation:\n'
printf '%q ' "$WORK/venv/bin/python" "$ROOT/scripts/validate_native.py" --rcc-source "$WORK/rcc/rcc-revas-eval/v0.1.0/runtime" --veritas-source "$WORK/veritas" --agentdojo-source "$WORK/agentdojo" --tau-source "$WORK/tau" --tau2-source "$WORK/tau2" --output "$ROOT/native-validation-new"
printf '\n'
