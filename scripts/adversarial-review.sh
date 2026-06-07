#!/usr/bin/env bash
# Adversarial code reviewer — the shared core for all defense-in-depth gates
# (on-demand, pre-push hook, CI). Feeds a git diff to a reviewer with a red-team
# prompt and a strict findings contract, then sets its exit code from the verdict.
#
# Engines (privacy matters — pick per data sensitivity):
#   claude  (default)  headless `claude -p`, stays in the Anthropic boundary.
#   local              an OpenAI-compatible LOCAL server (LM Studio / Ollama).
#                      Your code never leaves the machine — use for sensitive repos.
#
# Usage:
#   review.sh [--engine claude|local] [--staged] [--base <ref>]
#             [--threshold critical|high|medium] [--timeout <sec>]
#
# Local engine env (defaults shown):
#   LMSTUDIO_URL=http://localhost:1234/v1   # LM Studio server (Ollama: .../v1)
#   LMSTUDIO_MODEL=<auto>                    # else first model from /models
#
# Exit: 0 = PASS, 1 = BLOCK (finding >= threshold), 2 = usage/error.
set -euo pipefail

ENGINE="local"   # default to the private, no-credit local engine; opt into --engine claude
THRESHOLD="high"
MODE="working"
BASE=""
TIMEOUT="300"
LMSTUDIO_URL="${LMSTUDIO_URL:-http://localhost:1234/v1}"
LMSTUDIO_MODEL="${LMSTUDIO_MODEL:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --engine) ENGINE="${2:?}"; shift 2 ;;
    --staged) MODE="staged"; shift ;;
    --base) MODE="base"; BASE="${2:?--base needs a ref}"; shift 2 ;;
    --threshold) THRESHOLD="${2:?}"; shift 2 ;;
    --timeout) TIMEOUT="${2:?}"; shift 2 ;;
    -h|--help) sed -n '2,24p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

case "$MODE" in
  staged) DIFF="$(git diff --cached)" ;;
  base)
    git rev-parse --verify --quiet "${BASE}" >/dev/null 2>&1 \
      || { echo "[review] base ref '${BASE}' not found" >&2; exit 2; }
    # Two-dot net diff (base -> HEAD): robust even when base is the empty tree or
    # has no merge-base with HEAD (first push, unrelated histories).
    DIFF="$(git diff "${BASE}" HEAD)" ;;
  *)      DIFF="$(git diff)" ;;
esac

if [[ -z "${DIFF//[$' \t\n']/}" ]]; then
  echo "No changes to review."
  exit 0
fi

read -r -d '' INSTRUCTIONS <<EOF || true
You are an ADVERSARIAL code reviewer. Assume the diff is wrong until proven
otherwise. Find defects, do not praise. Review ONLY the diff.

For every issue, one line:
  [SEVERITY] path:line — what is wrong and why — concrete fix
Severities: CRITICAL (security/data-loss/crash) | HIGH (incorrect behavior,
missing error handling) | MEDIUM (robustness/maintainability) | LOW (nits).

Rules: be specific and falsifiable; no vague "consider". Do not invent issues.
If a band is clean after real scrutiny, say so explicitly. Watch for injection,
auth/permission gaps, unvalidated input, leaks, races, swallowed errors, off-by-one,
and silent behavior changes.

End with EXACTLY one final line:
  VERDICT: BLOCK   (if any finding is at/above ${THRESHOLD})
  VERDICT: PASS    (otherwise)
EOF

# Portable timeout (macOS lacks `timeout`; coreutils provides `gtimeout`).
run_to() {
  if command -v timeout >/dev/null 2>&1; then timeout "$TIMEOUT" "$@"
  elif command -v gtimeout >/dev/null 2>&1; then gtimeout "$TIMEOUT" "$@"
  else "$@"; fi
}

case "$ENGINE" in
  claude)
    command -v claude >/dev/null || { echo "claude CLI not found" >&2; exit 2; }
    PROMPT="${INSTRUCTIONS}

\`\`\`diff
${DIFF}
\`\`\`"
    OUT="$(run_to claude -p "$PROMPT" --permission-mode plan 2>/dev/null || true)"
    ;;
  local)
    command -v python3 >/dev/null || { echo "python3 not found" >&2; exit 2; }
    OUT="$(REV_INSTRUCTIONS="$INSTRUCTIONS" REV_DIFF="$DIFF" LM_URL="$LMSTUDIO_URL" \
           LM_MODEL="$LMSTUDIO_MODEL" REV_TIMEOUT="$TIMEOUT" python3 - <<'PY'
import os, json, sys, urllib.request
url = os.environ["LM_URL"].rstrip("/")
model = os.environ.get("LM_MODEL", "")
timeout = int(os.environ.get("REV_TIMEOUT", "300"))
try:
    if not model:
        with urllib.request.urlopen(url + "/models", timeout=15) as r:
            model = json.load(r)["data"][0]["id"]
    payload = {
        "model": model, "temperature": 0.2, "stream": False,
        "messages": [
            {"role": "system", "content": os.environ["REV_INSTRUCTIONS"]},
            {"role": "user", "content": "```diff\n" + os.environ["REV_DIFF"] + "\n```"},
        ],
    }
    req = urllib.request.Request(url + "/chat/completions",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        print(json.load(r)["choices"][0]["message"]["content"])
except Exception as e:
    print(f"[local engine error] could not reach a model at {url}: {e}", file=sys.stderr)
    sys.exit(2)
PY
)" || { echo "$OUT"; exit 2; }
    ;;
  *) echo "unknown engine: $ENGINE (use claude|local)" >&2; exit 2 ;;
esac

printf '%s\n' "$OUT"

# Loud-fail: a missing VERDICT means the reviewer errored or returned nothing
# usable (e.g. no API credit, model unreachable). Never treat that as a silent
# PASS — exit 2 so each gate decides how to handle an unavailable reviewer.
if grep -qE '^VERDICT:[[:space:]]*BLOCK' <<<"$OUT"; then
  exit 1
elif grep -qE '^VERDICT:[[:space:]]*PASS' <<<"$OUT"; then
  exit 0
else
  echo "[review] no VERDICT produced — reviewer failed or returned nothing usable (engine: ${ENGINE})" >&2
  exit 2
fi
