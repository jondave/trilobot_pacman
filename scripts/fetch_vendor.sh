#!/usr/bin/env bash
# Download pinned frontend libraries from the npm registry into
# control_scripts/blockly/static/vendor/ (not tracked in git).
set -euo pipefail

BLOCKLY_VERSION=12.5.1
MONACO_VERSION=0.52.2

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENDOR="$ROOT/control_scripts/blockly/static/vendor"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

fetch() { # name version
  curl -fsSL --retry 3 -o "$TMP/$1.tgz" "https://registry.npmjs.org/$1/-/$1-$2.tgz"
  mkdir -p "$TMP/$1"
  tar -xzf "$TMP/$1.tgz" -C "$TMP/$1"
}

fetch blockly "$BLOCKLY_VERSION"
fetch monaco-editor "$MONACO_VERSION"

rm -rf "$VENDOR"
mkdir -p "$VENDOR/blockly" "$VENDOR/monaco/min"

cp "$TMP/blockly/package/blockly.min.js" "$VENDOR/blockly/"
[ -d "$TMP/blockly/package/media" ] && cp -r "$TMP/blockly/package/media" "$VENDOR/blockly/media"
cp -r "$TMP/monaco-editor/package/min/vs" "$VENDOR/monaco/min/vs"

echo "Vendored blockly $BLOCKLY_VERSION and monaco-editor $MONACO_VERSION into $VENDOR"
