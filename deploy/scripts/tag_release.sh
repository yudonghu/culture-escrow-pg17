#!/usr/bin/env bash
# Create and push a versioned release tag.
#
# Usage: ./deploy/scripts/tag_release.sh <tag> [message]
#   tag      e.g. v1.0.0
#   message  optional, defaults to "Release <tag>"
#
# Example:
#   ./deploy/scripts/tag_release.sh v1.0.0 "S3 permanent storage + cleanup cron"

set -euo pipefail

TAG="${1:?Usage: tag_release.sh <tag> [message]}"
MSG="${2:-Release $TAG}"

# Validate semver-ish format
if ! echo "$TAG" | grep -qE '^v[0-9]+\.[0-9]+\.[0-9]+$'; then
    echo "[ERROR] tag must be vMAJOR.MINOR.PATCH (e.g. v1.0.0), got: $TAG"
    exit 1
fi

# Must be on main and up to date
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "[ERROR] must be on main branch (currently on $CURRENT_BRANCH)"
    exit 1
fi

git pull --ff-only origin main

git tag -a "$TAG" -m "$MSG"
git push origin "$TAG"

echo "[OK] tagged $TAG and pushed to origin"
echo "[OK] commit: $(git rev-parse --short HEAD)"
