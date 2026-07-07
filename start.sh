#!/usr/bin/env bash
# start.sh – KX-Bridge starten (zieht das fertige Image aus der Registry)

set -euo pipefail

cd "$(dirname "$0")"

IMAGE_BASE="gitea.it-drui.de/viewit/kx-bridge"

# .env anlegen falls nicht vorhanden
if [[ ! -f .env ]]; then
    if [[ -f .env.example ]]; then
        cp .env.example .env
        echo "[start] .env aus .env.example erstellt"
    else
        touch .env
    fi
fi

# config/ Verzeichnis und config.ini.example anlegen falls nicht vorhanden
mkdir -p config
if [[ ! -f config/config.ini ]] && [[ ! -f config/config.ini.example ]]; then
    if [[ -f config.ini.example ]]; then
        cp config.ini.example config/config.ini.example
        echo "[start] config/config.ini.example aus config.ini.example erstellt"
    fi
fi

# Docker verfügbar?
if ! docker info > /dev/null 2>&1; then
    echo "[start] Docker nicht gefunden – bitte Docker installieren."
    exit 1
fi

# Release-Kanal abfragen
CHANNEL=""
if [[ "${1:-}" == "stable" || "${1:-}" == "nightly" ]]; then
    CHANNEL="$1"
else
    echo ""
    echo "  Welchen Release-Kanal möchtest du starten?"
    echo "    1) stable   (empfohlen)"
    echo "    2) nightly  (getestete Vorabversion)"
    echo -n "  Auswahl [1]: "
    read -r CHOICE
    case "$CHOICE" in
        2) CHANNEL="nightly" ;;
        *) CHANNEL="stable" ;;
    esac
fi

if [[ "$CHANNEL" == "nightly" ]]; then
    IMAGE_TAG="nightly"
else
    IMAGE_TAG="latest"
fi
IMAGE="$IMAGE_BASE:$IMAGE_TAG"

echo "[start] Kanal: $CHANNEL  →  Image: $IMAGE"
echo "[start] Ziehe aktuelles Image ..."
docker pull "$IMAGE"

# docker-compose.yml auf den gewählten Kanal umschreiben (nur die image-Zeile)
if [[ -f docker-compose.yml ]]; then
    sed -i.bak -E "s#^(\s*image:\s*).*#\1$IMAGE#" docker-compose.yml
    rm -f docker-compose.yml.bak
fi

# Container starten
echo "[start] Starte KX-Bridge ..."
docker-compose down 2>/dev/null || true
docker-compose up -d

echo ""
echo "  ✓ KX-Bridge läuft ($CHANNEL)"
echo "  Web-UI : http://$(hostname -I | awk '{print $1}'):7125"
echo "  Logs   : docker-compose logs -f"
echo "  Stop   : docker-compose down"
