#!/usr/bin/env bash
# start.sh – KX-Bridge starten (baut Docker-Image automatisch wenn nötig)

set -euo pipefail

cd "$(dirname "$0")"

# .env anlegen falls nicht vorhanden
if [[ ! -f .env ]]; then
    if [[ -f .env.example ]]; then
        cp .env.example .env
        echo "[start] .env aus .env.example erstellt"
    else
        touch .env
    fi
fi

# Docker verfügbar?
if ! docker info > /dev/null 2>&1; then
    echo "[start] Docker nicht gefunden – bitte Docker installieren."
    exit 1
fi

# Prüfen ob Build nötig ist
NEEDS_BUILD=0
if ! docker image inspect kx-bridge:latest > /dev/null 2>&1; then
    echo "[start] Image nicht vorhanden – baue kx-bridge:latest ..."
    NEEDS_BUILD=1
else
    # Image-Erstellungszeit in Unix-Sekunden
    IMAGE_TS=$(docker inspect --format='{{.Created}}' kx-bridge:latest \
        | python3 -c "import sys,datetime; s=sys.stdin.read().strip(); \
          s=s[:26].rstrip('Z').replace('T',' '); \
          print(int(datetime.datetime.fromisoformat(s).replace(tzinfo=datetime.timezone.utc).timestamp()))" 2>/dev/null || echo 0)

    for f in Dockerfile \
              bridge/kobrax_moonraker_bridge.py \
              bridge/kobrax_client.py \
              bridge/env_loader.py \
              bridge/requirements.txt \
              bridge/anycubic_slicer.crt \
              bridge/anycubic_slicer.key; do
        if [[ -f "$f" ]]; then
            FILE_TS=$(python3 -c "import os; print(int(os.path.getmtime('$f')))" 2>/dev/null || echo 0)
            if [[ $FILE_TS -gt $IMAGE_TS ]]; then
                echo "[start] '$f' ist neuer als das Image – baue neu ..."
                NEEDS_BUILD=1
                break
            fi
        fi
    done
fi

if [[ $NEEDS_BUILD -eq 1 ]]; then
    docker build -t kx-bridge:latest .
fi

# Container starten
echo "[start] Starte KX-Bridge ..."
docker-compose down 2>/dev/null || true
docker-compose up -d

echo ""
echo "  ✓ KX-Bridge läuft"
echo "  Web-UI : http://$(hostname -I | awk '{print $1}'):7125"
echo "  Logs   : docker-compose logs -f"
echo "  Stop   : docker-compose down"
