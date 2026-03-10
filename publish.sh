#!/bin/bash
# ============================================================
# Publish air-blackbox to PyPI
# ============================================================
# Prerequisites:
#   pip install build twine
#   Create account at pypi.org
#   Create API token at https://pypi.org/manage/account/token/
#
# Usage:
#   ./publish.sh          # Publish to PyPI
#   ./publish.sh test     # Publish to Test PyPI first
# ============================================================

set -e

echo "========================================"
echo "  Publishing air-blackbox to PyPI"
echo "========================================"

# Clean previous builds
rm -rf dist/ build/ sdk/*.egg-info

# Build
echo ">> Building package..."
python3 -m build

echo ""
echo ">> Package contents:"
ls -lh dist/

if [ "$1" = "test" ]; then
    echo ""
    echo ">> Uploading to TEST PyPI..."
    python3 -m twine upload --repository testpypi dist/*
    echo ""
    echo ">> Test install:"
    echo "   pip install --index-url https://test.pypi.org/simple/ air-blackbox"
else
    echo ""
    echo ">> Uploading to PyPI..."
    python3 -m twine upload dist/*
    echo ""
    echo ">> Verify install:"
    echo "   pip install air-blackbox"
fi

echo ""
echo "========================================"
echo "  Done! air-blackbox published."
echo "========================================"
