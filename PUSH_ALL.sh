#!/bin/bash
# ============================================
# PUSH ALL PENDING CHANGES
# Run from anywhere. Copy-paste the whole thing.
# ============================================

set -e

echo "=========================================="
echo "1/4  Pushing airblackbox-site (Console + website updates)"
echo "=========================================="
cd ~/Desktop/airblackbox-site
git push origin main
echo ""

echo "=========================================="
echo "2/4  Deploying airblackbox-site to Vercel"
echo "=========================================="
vercel deploy --prod
echo ""

echo "=========================================="
echo "3/4  Pushing gateway (README, PRD, cleanup)"
echo "=========================================="
cd ~/Desktop/gateway

# Move marketing files out of root (already done locally, stage the moves)
git rm --cached air-gate-README.md air-platform-README.md compliance-action-README.md gateway-README.md README_TEMPLATE.md 2>/dev/null || true

# Stage everything
git add README.md PRD_CONSOLE.md ORG_PROFILE_README.md
git add content/readmes/ content/drafts/
git add -A

git commit -m "docs: add Console PRD, clean marketing files from root, add org profile README

- PRD_CONSOLE.md: product spec for paid Console UI
- ORG_PROFILE_README.md: unified org profile matching gateway positioning
- Moved marketing/draft files to content/readmes/ and content/drafts/
- Gateway README already updated with ML-DSA-65, 51+ checks, full ecosystem

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"

git push origin main
echo ""

echo "=========================================="
echo "4/4  Update .github org profile README"
echo "=========================================="
echo ""
echo "MANUAL STEP: The org profile README needs to go to airblackbox/.github"
echo ""
echo "If you have the .github repo cloned:"
echo "  cd ~/Desktop/.github   # or wherever it is"
echo "  cp ~/Desktop/gateway/ORG_PROFILE_README.md profile/README.md"
echo "  git add profile/README.md"
echo '  git commit -m "docs: align org profile with current positioning"'
echo "  git push origin main"
echo ""
echo "If you don't have it cloned:"
echo "  git clone https://github.com/airblackbox/.github.git"
echo "  cd .github"
echo "  mkdir -p profile"
echo "  cp ~/Desktop/gateway/ORG_PROFILE_README.md profile/README.md"
echo "  git add profile/README.md"
echo '  git commit -m "docs: align org profile with current positioning"'
echo "  git push origin main"
echo ""

echo "=========================================="
echo "DONE. Verify at:"
echo "  https://airblackbox.ai/console"
echo "  https://airblackbox.ai/console/scan"
echo "  https://github.com/airblackbox"
echo "  https://github.com/airblackbox/airblackbox"
echo "=========================================="
