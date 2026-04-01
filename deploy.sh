#!/usr/bin/env bash
# ============================================================
# Ars Magna Scientiarum — Deploy to Hugging Face Spaces
# ============================================================
# Just pushes code. All data ingestion happens IN the Space.
#
# Prerequisites:
#   pip install huggingface_hub
#   huggingface-cli login
# ============================================================

set -e

HF_USERNAME="${1:-rainvare}"
SPACE_NAME="ars-magna-scientiarum"

echo "🔮 Deploying Ars Magna Scientiarum to HF Spaces..."
echo "   Space: ${HF_USERNAME}/${SPACE_NAME}"
echo ""

# Create temp deploy dir
DEPLOY_DIR=$(mktemp -d)
ORIG_DIR=$(pwd)

# Try to clone existing space, or create new one
if ! git clone "https://huggingface.co/spaces/${HF_USERNAME}/${SPACE_NAME}" "${DEPLOY_DIR}/space" 2>/dev/null; then
    echo "📦 Creating new Space..."
    huggingface-cli repo create "${SPACE_NAME}" --type space -y
    git clone "https://huggingface.co/spaces/${HF_USERNAME}/${SPACE_NAME}" "${DEPLOY_DIR}/space"
fi

cd "${DEPLOY_DIR}/space"

# Copy HF_README as the Space README (has YAML metadata)
cp "${ORIG_DIR}/HF_README.md" README.md

# Copy application files
cp "${ORIG_DIR}/Dockerfile" .
cp "${ORIG_DIR}/start.sh" .
cp "${ORIG_DIR}/requirements.txt" .
cp "${ORIG_DIR}/app.py" .
cp "${ORIG_DIR}/spike_openalex.py" .
cp "${ORIG_DIR}/enrich_nodes.py" .
cp "${ORIG_DIR}/.dockerignore" .

mkdir -p core
cp "${ORIG_DIR}/core/__init__.py" core/
cp "${ORIG_DIR}/core/engine.py" core/

# Push
git add -A
git commit -m "Deploy Ars Magna Scientiarum v1.0" || echo "No changes to commit"
git push origin main

echo ""
echo "✅ Deployed! Your Space will be at:"
echo "   https://huggingface.co/spaces/${HF_USERNAME}/${SPACE_NAME}"
echo ""
echo "⚠️  Don't forget to add GROQ_API_KEY as a secret in Space settings!"
echo "   And enable persistent storage to avoid re-downloading on restart."

cd "${ORIG_DIR}"
rm -rf "${DEPLOY_DIR}"
