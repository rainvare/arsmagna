#!/usr/bin/env bash
set -e

echo "🔮 ARS MAGNA SCIENTIARUM — Starting..."

DATA_DIR="/app/data"
mkdir -p "${DATA_DIR}"
export ARS_DATA_DIR="${DATA_DIR}"

BASE="${DATA_DIR}/science_graph.json"

if [ ! -f "${BASE}" ]; then
    echo "🌐 Downloading from OpenAlex..."
    python /app/spike_openalex.py
fi

echo "🚀 Launching Streamlit..."
exec streamlit run /app/app.py \
    --server.port=7860 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.maxUploadSize=50 \
    --browser.gatherUsageStats=false
