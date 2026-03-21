#!/usr/bin/env bash
# Update the Homebrew formula after cutting a new release.
#
# Usage:
#   ./scripts/update-formula.sh 0.3.0
#
# What it does:
#   1. Tags and pushes the new version in the main repo
#   2. Computes the sha256 of the release tarball
#   3. Updates the formula url + sha256
#   4. Regenerates Python resource hashes via `brew update-python-resources`
#
set -euo pipefail

VERSION="${1:?Usage: $0 <version> (e.g. 0.3.0)}"
FORMULA="$(dirname "$0")/../Formula/claude-agent-os.rb"
TARBALL_URL="https://github.com/travis-burmaster/claude-telegram-agent/archive/refs/tags/v${VERSION}.tar.gz"

echo "==> Fetching tarball to compute sha256..."
SHA256=$(curl -sL "$TARBALL_URL" | shasum -a 256 | awk '{print $1}')
echo "    sha256: $SHA256"

echo "==> Updating formula url and sha256..."
sed -i '' \
  -e "s|archive/refs/tags/v[0-9.]*\.tar\.gz|archive/refs/tags/v${VERSION}.tar.gz|" \
  -e "s|sha256 \"[a-f0-9]*\"|sha256 \"${SHA256}\"|" \
  "$FORMULA"

echo "==> Regenerating Python resource hashes..."
if command -v brew &>/dev/null; then
  brew update-python-resources "$(dirname "$FORMULA")/claude-agent-os.rb" || \
    echo "WARN: brew update-python-resources failed — update resource hashes manually"
else
  echo "WARN: brew not found — skipping resource hash update"
fi

echo ""
echo "Done! Review the changes in Formula/claude-agent-os.rb, then commit and push."
echo ""
echo "  git add Formula/claude-agent-os.rb"
echo "  git commit -m 'chore: bump formula to v${VERSION}'"
echo "  git push"
