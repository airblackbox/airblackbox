#!/bin/bash
# Deploy airblackbox.ai 404 fixes
# Run this from any directory — it clones, patches, and pushes.

set -e

echo "🔧 Deploying airblackbox.ai 404 fixes..."

# Get the directory where this script lives
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Clone the site repo to a temp directory
TMPDIR=$(mktemp -d)
cd "$TMPDIR"
git clone https://github.com/airblackbox/airblackbox-site.git
cd airblackbox-site

# Apply the patch
git am "$SCRIPT_DIR/airblackbox-site-404-fixes.patch"

# Push to GitHub (triggers Vercel auto-deploy)
git push origin main

echo ""
echo "✅ Pushed to GitHub. Vercel will auto-deploy in ~30 seconds."
echo ""
echo "Fixes deployed:"
echo "  • /privacy — new privacy policy page"
echo "  • /6-technical-checks — redirects to /blog/6-technical-checks"
echo "  • Schema.org — replaced invalid programmingLanguage with aggregateRating"
echo "  • Email encoding — all @ symbols encoded as &#64; to prevent"
echo "    Cloudflare email obfuscation creating /cdn-cgi/l/email-protection 404s"
echo ""
echo "Verify at: https://airblackbox.ai/privacy"

# Cleanup
rm -rf "$TMPDIR"
