#!/usr/bin/env bash
set -euo pipefail

RELEASE_TAG="${1:-nudenet-assets-v1}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MODELS_DIR="${REPO_ROOT}/models"

mkdir -p "${MODELS_DIR}"

gh release download "${RELEASE_TAG}" \
  -R treehorn-dev/ffmpeg-onnx \
  -D "${MODELS_DIR}" \
  -p "nudenet.onnx" \
  -p "labels.txt"

