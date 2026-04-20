#!/usr/bin/env bash
# Roll back production to a specific release tag.
#
# Usage: ./deploy/scripts/rollback_prod.sh <tag> [root]
#   tag   e.g. v1.0.0  — must be an existing git tag
#   root  deploy root, defaults to /opt/services/culture-escrow-pg17
#
# Example (run on EC2):
#   bash /opt/services/culture-escrow-pg17/deploy/scripts/rollback_prod.sh v1.0.0

set -euo pipefail

TAG="${1:?Usage: rollback_prod.sh <tag> [root]}"
ROOT="${2:-/opt/services/culture-escrow-pg17}"

echo "[rollback] target=$TAG root=$ROOT"
bash "$ROOT/deploy/scripts/deploy_prod.sh" "$ROOT" "$TAG"
