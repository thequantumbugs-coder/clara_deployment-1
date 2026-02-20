#!/bin/bash
# Push this repository to https://github.com/thequantumbugs-coder/FB-Clara.git
# Run from the project root. Requires GitHub auth (HTTPS token or SSH key).
set -e
cd "$(dirname "$0")"
REMOTE="${1:-fb-clara}"
echo "Pushing main to remote: $REMOTE"
git push "$REMOTE" main
echo "Done. Open https://github.com/thequantumbugs-coder/FB-Clara"
