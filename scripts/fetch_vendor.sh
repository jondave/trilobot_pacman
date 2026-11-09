#!/usr/bin/env bash
# Download pinned frontend libraries from the npm registry into
# control_scripts/blockly/static/vendor/ (not tracked in git).
set -euo pipefail

BLOCKLY_VERSION=12.5.1
MONACO_VERSION=0.52.2
FONTAWESOME_VERSION=5.15.4
MARKED_VERSION=16.4.2
DOMPURIFY_VERSION=3.4.15

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENDOR="$ROOT/control_scripts/blockly/static/vendor"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

fetch() { # package version (a scoped @scope/name package unpacks into $TMP/name)
  local name="${1##*/}"
  curl -fsSL --retry 3 -o "$TMP/$name.tgz" "https://registry.npmjs.org/$1/-/$name-$2.tgz"
  mkdir -p "$TMP/$name"
  tar -xzf "$TMP/$name.tgz" -C "$TMP/$name"
}

fetch blockly "$BLOCKLY_VERSION"
fetch monaco-editor "$MONACO_VERSION"
fetch @fortawesome/fontawesome-free "$FONTAWESOME_VERSION"
fetch marked "$MARKED_VERSION"
fetch dompurify "$DOMPURIFY_VERSION"

rm -rf "$VENDOR"
mkdir -p "$VENDOR/blockly" "$VENDOR/monaco/min" "$VENDOR/fontawesome/css" \
  "$VENDOR/marked" "$VENDOR/dompurify"

cp "$TMP/blockly/package/blockly.min.js" "$VENDOR/blockly/"
[ -d "$TMP/blockly/package/media" ] && cp -r "$TMP/blockly/package/media" "$VENDOR/blockly/media"
cp -r "$TMP/monaco-editor/package/min/vs" "$VENDOR/monaco/min/vs"
# all.min.css loads its fonts from ../webfonts/, so keep that layout.
cp "$TMP/fontawesome-free/package/css/all.min.css" "$VENDOR/fontawesome/css/"
cp -r "$TMP/fontawesome-free/package/webfonts" "$VENDOR/fontawesome/webfonts"
cp "$TMP/fontawesome-free/package/LICENSE.txt" "$VENDOR/fontawesome/"
# marked renders the Python reference; DOMPurify sanitises its HTML.
cp "$TMP/marked/package/lib/marked.umd.js" "$TMP/marked/package/LICENSE.md" "$VENDOR/marked/"
cp "$TMP/dompurify/package/dist/purify.min.js" "$TMP/dompurify/package/LICENSE" "$VENDOR/dompurify/"

echo "Vendored blockly $BLOCKLY_VERSION, monaco-editor $MONACO_VERSION," \
  "fontawesome-free $FONTAWESOME_VERSION, marked $MARKED_VERSION and" \
  "dompurify $DOMPURIFY_VERSION into $VENDOR"
