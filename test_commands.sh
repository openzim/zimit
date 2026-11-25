#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_NO_TRANSLATE="${ROOT_DIR}/output-no-translate"
OUT_WITH_TRANSLATE="${ROOT_DIR}/output-with-translate"

SEED_URL="https://quotes.toscrape.com/page/1/"
PAGE_LIMIT="10"

mkdir -p "${OUT_NO_TRANSLATE}" "${OUT_WITH_TRANSLATE}"

echo "Building Docker image zimit:latest from ${ROOT_DIR}/Dockerfile"
# docker build -t zimit:latest "${ROOT_DIR}"

echo "Running crawl without translation"
docker run --rm \
  -v "${OUT_NO_TRANSLATE}:/output" \
  zimit:latest zimit \
  --seeds "${SEED_URL}" \
  --pageLimit "${PAGE_LIMIT}" \
  --name "quotes-no-translate"

echo "Running crawl with translation enabled"
docker run --rm \
  -v "${OUT_WITH_TRANSLATE}:/output" \
  zimit:latest zimit \
  --seeds "${SEED_URL}" \
  --pageLimit "${PAGE_LIMIT}" \
  --translate "es" \
  --name "quotes-with-translate"

echo "Done."
echo "Outputs:"
echo "  - ${OUT_NO_TRANSLATE}"
echo "  - ${OUT_WITH_TRANSLATE}"
