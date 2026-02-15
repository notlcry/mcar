#!/usr/bin/env bash
#
# new-module.sh — Generate a new mcar capability module from template.
#
# Usage:
#   ./scripts/new-module.sh <module_id> [description]
#
# Example:
#   ./scripts/new-module.sh camera "Camera capture module"
#
# Generates:
#   modules/<module_id>/module.py
#   modules/<module_id>/capabilities.json
#   modules/<module_id>/__init__.py
#   modules/tests/test_<module_id>_module.py

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE_DIR="$PROJECT_ROOT/modules/template"
MODULES_DIR="$PROJECT_ROOT/modules"

# ─── Argument parsing ───────────────────────────────────

if [ $# -lt 1 ]; then
    echo "Usage: $0 <module_id> [description]"
    echo "  module_id   — snake_case identifier (e.g., camera, ir_sensor)"
    echo "  description — human-readable description (optional)"
    exit 1
fi

MODULE_ID="$1"
MODULE_DESCRIPTION="${2:-${MODULE_ID} module}"

# ─── Validate module_id ─────────────────────────────────

if ! echo "$MODULE_ID" | grep -qE '^[a-z][a-z0-9_]*$'; then
    echo "Error: module_id must be snake_case (lowercase letters, digits, underscores, starting with a letter)"
    exit 1
fi

# ─── Check for existing module ──────────────────────────

MODULE_DIR="$MODULES_DIR/$MODULE_ID"
if [ -d "$MODULE_DIR" ]; then
    echo "Error: Module directory already exists: $MODULE_DIR"
    exit 1
fi

# ─── Convert snake_case to PascalCase ───────────────────

to_pascal_case() {
    echo "$1" | sed 's/_/ /g' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) substr($i,2)}1' | sed 's/ //g'
}

MODULE_CLASS="$(to_pascal_case "$MODULE_ID")"

# ─── Generate files ─────────────────────────────────────

echo "Creating module: $MODULE_ID ($MODULE_CLASS)"
mkdir -p "$MODULE_DIR"

# Process each template file
for tmpl in "$TEMPLATE_DIR"/*.tmpl; do
    filename="$(basename "$tmpl" .tmpl)"
    dest="$MODULE_DIR/$filename"

    sed -e "s/__MODULE_ID__/${MODULE_ID}/g" \
        -e "s/__MODULE_CLASS__/${MODULE_CLASS}/g" \
        -e "s/__MODULE_DESCRIPTION__/${MODULE_DESCRIPTION}/g" \
        "$tmpl" > "$dest"

    echo "  Created: $dest"
done

# Generate test file
TEST_DEST="$MODULES_DIR/tests/test_${MODULE_ID}_module.py"
sed -e "s/__MODULE_ID__/${MODULE_ID}/g" \
    -e "s/__MODULE_CLASS__/${MODULE_CLASS}/g" \
    -e "s/__MODULE_DESCRIPTION__/${MODULE_DESCRIPTION}/g" \
    "$TEMPLATE_DIR/test_module.py.tmpl" > "$TEST_DEST"

echo "  Created: $TEST_DEST"

echo ""
echo "Module '$MODULE_ID' created successfully!"
echo ""
echo "Next steps:"
echo "  1. Edit $MODULE_DIR/capabilities.json — define your capabilities"
echo "  2. Edit $MODULE_DIR/module.py — implement invoke handlers"
echo "  3. Run tests: python -m pytest $TEST_DEST -v"
