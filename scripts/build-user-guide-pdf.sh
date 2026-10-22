#!/usr/bin/env bash
# Regenerates Guia-do-Usuario-BR-Crono-Desktop.pdf from README.md and imagens/.
# Run from the repository root, passing the app release the guide describes:
#   ./scripts/build-user-guide-pdf.sh 0.2.0
# Needs Python 3 with reportlab (pip install reportlab).
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "usage: $0 <app version, e.g. 0.2.0>" >&2
  exit 2
fi

python3 ./scripts/generate_user_guide_pdf.py \
  --logo './assets/Logo CB.png' \
  --release-version "v$1"

echo "User guide PDF ready: ./Guia-do-Usuario-BR-Crono-Desktop.pdf"
