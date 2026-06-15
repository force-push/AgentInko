#!/usr/bin/env bash
# AgentInko — finish git setup and push to the `force-push` account.
#
# Why this script exists: the build sandbox can't complete git operations (the
# mounted folder blocks .git lock-file changes) and has no network access to
# GitHub or to your credentials. So run this locally — it produces a clean,
# well-documented commit history and pushes.
#
# Usage:
#   ./setup_git.sh [remote-url]
# e.g.
#   ./setup_git.sh git@github.com:force-push/AgentInko.git
#   ./setup_git.sh                       # commits only; add remote/push yourself
#
set -uo pipefail
cd "$(dirname "$0")"

REMOTE_URL="${1:-}"

# 1. Clear any stale lock files left by the sandbox (harmless if none exist).
rm -f .git/*.lock .git/objects/*.lock .git/objects/maintenance.lock 2>/dev/null || true

# 2. Init if needed; settle git identity.
[ -d .git ] || git init -b main
git config user.name  "Kym McInerney"
git config user.email "kym.mcinerney@gmail.com"
# Avoid background maintenance that can re-create locks.
git config gc.auto 0
git config maintenance.auto false

# 3. Commit in logical chunks. Each commit only fires if it has staged changes,
#    so re-running the script is safe and only commits what's new.
commit_group () {
  local msg="$1"; shift
  git add -- "$@" 2>/dev/null || true
  if ! git diff --cached --quiet; then
    git commit -q -m "$msg"
    echo "  committed: $msg"
  fi
}

commit_group "Incentive framework: outcome-contingent rewards with guardrails" \
  .gitignore incentivised-agents-plan.md \
  agent_incentive/incentive_framework.py agent_incentive/example_agent.py \
  agent_incentive/test_incentive_framework.py

commit_group "Godot Tier 1 slice: minimal game + build-integrity verifier" \
  godot-agentinko-guidance.md godot_game \
  agent_incentive/godot_verifier.py agent_incentive/godot_demo.py \
  agent_incentive/test_godot_verifier.py

commit_group "MCP connection + model gateway + skills (Claude design / Kimi build)" \
  agent_incentive/model_gateway.py agent_incentive/godot_mcp_client.py \
  agent_incentive/mock_godot_mcp.py agent_incentive/skills.py

commit_group "Tier 2 playtest agent + full pipeline" \
  agent_incentive/playtest_agent.py agent_incentive/pipeline_demo.py \
  agent_incentive/test_pipeline.py

commit_group "Octopus dashboard: local web UI over the live pipeline" \
  dashboard

commit_group "Game concepts + Camouflage storyboard spec (v2)" \
  game-concepts.md games

commit_group "Docs + market strategy + project README/changelog" \
  README.md CHANGELOG.md market-strategy.md setup_git.sh

# Catch anything not explicitly grouped above.
commit_group "Misc project files" .

# 4. Remote + push.
if [ -z "$REMOTE_URL" ]; then
  echo
  echo ">> Commits done. To push, add your remote and run:"
  echo "   git remote add origin <force-push-url>"
  echo "   git push -u origin main"
  exit 0
fi

if git remote | grep -q '^origin$'; then
  git remote set-url origin "$REMOTE_URL"
else
  git remote add origin "$REMOTE_URL"
fi
git push -u origin main
echo "Pushed to $REMOTE_URL"
