#!/usr/bin/env bash
# test_install.sh – Smoke-Test: Release-Repo klonen, start.sh ausführen, HTTP prüfen.
#
# Simuliert den Weg eines anonymen Nutzers:
#   1. Release-Repo klonen
#   2. start.sh ausführen (baut Docker-Image, startet Container)
#   3. HTTP-Endpunkte prüfen
#   4. Aufräumen
#
# Voraussetzung: Docker installiert, Port 7125 frei
#
# Verwendung:
#   bash tests/test_install.sh

set -euo pipefail

GITEA_URL="https://gitea.it-drui.de/viewit/KX-Bridge-Release"
WORK_DIR=$(mktemp -d /tmp/kx-bridge-test-XXXXXX)
PASS=0; FAIL=0

ok()   { echo "  ✓ $*"; PASS=$((PASS+1)); }
fail() { echo "  ✗ $*"; FAIL=$((FAIL+1)); }

cleanup() {
    echo ""
    echo "[cleanup] Stoppe Container und lösche Testverzeichnis ..."
    cd "$WORK_DIR/KX-Bridge-Release" 2>/dev/null && docker-compose down 2>/dev/null || true
    rm -rf "$WORK_DIR"
}
trap cleanup EXIT

echo "=== KX-Bridge Installations-Smoke-Test ==="
echo ""

# ── Schritt 1: Repo klonen ────────────────────────────────────────────────────
echo "[1/5] Klone Release-Repo ..."
git clone --depth=1 "$GITEA_URL" "$WORK_DIR/KX-Bridge-Release" > /dev/null 2>&1 \
    && ok "Repo geklont" \
    || { fail "git clone fehlgeschlagen"; exit 1; }

cd "$WORK_DIR/KX-Bridge-Release"

# ── Schritt 2: Erwartete Dateien vorhanden ────────────────────────────────────
echo "[2/5] Prüfe Dateien im Repo ..."
for f in start.sh docker-compose.yml Dockerfile kobrax_moonraker_bridge.py \
          anycubic_slicer.crt anycubic_slicer.key .env.example; do
    [[ -f "$f" ]] && ok "$f vorhanden" || fail "$f FEHLT"
done

# Dockerfile darf keine 05_scripts/-Pfade enthalten
if grep -q "05_scripts/" Dockerfile; then
    fail "Dockerfile enthält '05_scripts/' – falsches Dockerfile im Release-Repo!"
else
    ok "Dockerfile Pfade korrekt (kein 05_scripts/-Präfix)"
fi

# ── Schritt 3: start.sh ausführen ────────────────────────────────────────────
echo "[3/5] Führe start.sh aus ..."
chmod +x start.sh
./start.sh > /tmp/kx-bridge-start.log 2>&1 \
    && ok "start.sh erfolgreich" \
    || { fail "start.sh fehlgeschlagen (siehe /tmp/kx-bridge-start.log)"; cat /tmp/kx-bridge-start.log; exit 1; }

# Kurz warten bis Bridge hochgefahren
sleep 3

# ── Schritt 4: HTTP-Endpunkte prüfen ─────────────────────────────────────────
echo "[4/5] Prüfe HTTP-Endpunkte ..."
BASE="http://localhost:7125"

check_endpoint() {
    local path="$1"
    local desc="$2"
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE$path")
    [[ "$http_code" == "200" ]] \
        && ok "$desc ($path → $http_code)" \
        || fail "$desc ($path → $http_code)"
}

check_endpoint "/"                    "Web-UI (index.html)"
check_endpoint "/api/state"           "GET /api/state"
check_endpoint "/api/settings"        "GET /api/settings"
check_endpoint "/server/info"         "GET /server/info (Moonraker)"
check_endpoint "/printer/info"        "GET /printer/info (Moonraker)"
check_endpoint "/printer/objects/list" "GET /printer/objects/list"
check_endpoint "/api/version"         "GET /api/version (OctoPrint compat)"

# Beim ersten Start: printer_ip muss leer sein → Settings-Modal würde sich öffnen
SETTINGS=$(curl -s "$BASE/api/settings")
PRINTER_IP=$(echo "$SETTINGS" | python3 -c "import sys,json; print(json.load(sys.stdin).get('printer_ip',''))" 2>/dev/null || echo "ERROR")
[[ -z "$PRINTER_IP" ]] \
    && ok "Erstkonfiguration erkannt: printer_ip leer → Settings-Modal öffnet sich" \
    || fail "printer_ip sollte beim Erststart leer sein, ist: '$PRINTER_IP'"

# ── Schritt 5: Container läuft stabil ────────────────────────────────────────
echo "[5/5] Prüfe Container-Stabilität ..."
sleep 2
RUNNING=$(docker-compose ps --services --filter "status=running" 2>/dev/null || true)
[[ -n "$RUNNING" ]] \
    && ok "Container läuft stabil" \
    || fail "Container ist nicht mehr aktiv"

# ── Ergebnis ──────────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════"
echo "  Ergebnis: $PASS bestanden, $FAIL fehlgeschlagen"
echo "══════════════════════════════════════"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
