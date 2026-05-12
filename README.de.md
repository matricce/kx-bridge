<p align="center"><img src="knlogo.png" alt="KX-Bridge Logo" width="180"/></p>

# KX-Bridge – Anycubic Kobra X

**Version:** 0.9.8

Steuere deinen **Anycubic Kobra X** mit OrcaSlicer — ohne Klipper, ohne Raspberry Pi.  
KX-Bridge ist eine Moonraker-kompatible Bridge die direkt mit dem Drucker kommuniziert.

---

## Schnellstart in 3 Schritten

### Schritt 1 – Drucker vorbereiten

Den Kobra X in den LAN-Modus versetzen:  
**Drucker-Display → Einstellungen → LAN-Modus einschalten**

### Schritt 2 – Credentials holen

Die MQTT-Zugangsdaten sind druckerspezifisch und an die Hardware gebunden.

**Option A – fetch_credentials (empfohlen):**

```bash
fetch_credentials --ip 192.168.x.x --write-config
```

Holt die Credentials direkt per HTTP vom Drucker und schreibt sie automatisch in `config/config.ini`. Benötigt nur die Drucker-IP — kein Slicer nötig.

**Option B – extract_credentials (wenn Drucker-IP unbekannt):**

1. **AnycubicSlicerNext** öffnen und Drucker verbinden (bis Status angezeigt wird)
2. **`extract_credentials`** ausführen — gibt Username, Password, Device-ID und Drucker-IP aus
3. Werte im Web-UI eintragen (⚙-Menü)

> **Download:** [gitea.it-drui.de/viewit/KX-Bridge-Release/releases](https://gitea.it-drui.de/viewit/KX-Bridge-Release/releases) → `fetch_credentials` / `extract_credentials` (Linux & Windows) im jeweiligen Release-Asset

### Schritt 3 – Bridge starten

```bash
./start.sh
```

Das Skript baut das Docker-Image automatisch beim ersten Aufruf.

**Web-UI öffnen:** `http://BRIDGE-IP:7125`  
→ Das ⚙-Menü öffnet sich beim ersten Start automatisch  
→ Bei Option B: Credentials aus Schritt 2 eintragen → **Speichern & Neustart**

**OrcaSlicer verbinden:**  
Drucker → Verbindungstyp **Moonraker** → Host: `http://BRIDGE-IP:7125`

> **Wichtig:** Verbindungstyp muss **Moonraker** sein (nicht „Bambu" oder „Klipper").  
> Im Host-Feld vollständige URL mit `http://` und Port `:7125` angeben.

---

## 📺 Video Tutorial

[![KX-Bridge Setup & Bedienung](https://img.youtube.com/vi/1Ql4wfH27fM/hqdefault.jpg)](https://www.youtube.com/watch?v=1Ql4wfH27fM)

---

## ⚠️ Update von 0.9.1 oder älter

Ab **0.9.2** speichert KX-Bridge Einstellungen in `config/config.ini` statt in `.env`.

**Migration erfolgt automatisch** — keine manuelle Aktion nötig:
- Beim ersten Start nach dem Update liest die Bridge die vorhandene `.env` und erstellt `config/config.ini` automatisch
- Einstellungen bleiben ab sofort nach `docker-compose restart` und zukünftigen Updates erhalten
- Die `.env`-Datei bleibt read-only gemountet als Migrationsquelle — kann liegen bleiben
- Zum manuellen Anlegen einer `config.ini`: Vorlage unter `config/config.ini.example` kopieren

---

## Was wird unterstützt?

| Funktion | Details |
|----------|---------|
| Druckerstatus | Temperatur, Fortschritt, Zustand, Restzeit |
| Drucksteuerung | Start, Pause, Fortsetzen, Abbrechen |
| Temperaturregelung | Nozzle und Bett während des Drucks |
| Druckgeschwindigkeit | Leise / Normal / Sport |
| AMS-Farbwechsel | Filament einziehen / ausziehen |
| Licht & Lüfter | Drucklicht und Lüfterdrehzahl |
| Web-UI | Dashboard, Achsensteuerung, Kameraansicht |
| Self-Update | Neue Versionen direkt im Browser installieren |
| OrcaSlicer | Moonraker-Protokoll (HTTP + WebSocket) |

---

## Alternativen zu Docker

**Linux Binary** (kein Docker nötig):
```bash
chmod +x kx-bridge
./kx-bridge
```

**Python direkt:**
```bash
pip install aiohttp
python bridge/kobrax_moonraker_bridge.py
```

Web-UI jeweils unter `http://localhost:7125` — ⚙-Menü führt durch die Erstkonfiguration.

---

## Nützliche Befehle

```bash
# Logs anzeigen
docker-compose logs -f

# Bridge stoppen
docker-compose down

# Bridge neu starten (nach Update)
./start.sh
```

---

## Fehlerbehebung

**„Falsche MQTT-Zugangsdaten"** beim Start:
- `fetch_credentials --ip <Drucker-IP> --write-config` erneut ausführen und Bridge neu starten
- Wenn IP unbekannt: AnycubicSlicerNext neu starten, Drucker verbinden, `extract_credentials` erneut ausführen
- Nur die IP-Adresse ins Feld eintragen, keinen Port (✗ `192.168.1.102:9883` → ✓ `192.168.1.102`)

**Drucker nicht gefunden / kein LAN-Modus:**
- Am Drucker-Display: Einstellungen → LAN-Modus einschalten
- Drucker und Bridge müssen im selben Netzwerk sein

**Docker: Permission denied:**
```bash
sudo usermod -aG docker $USER  # dann neu einloggen
```

---

## Sicherheitshinweise

- Die Bridge ist im lokalen Netzwerk erreichbar unter `http://<Host-IP>:7125` — nicht ins Internet freigeben
- `config/config.ini` enthält Drucker-Credentials — nicht öffentlich teilen
- Credentials haben keinen Zugang zu Anycubic-Cloud-Diensten

---

## Lizenz & Rechtliches

Interoperabilitätsforschung gem. §69e UrhG — ausschließlich private, nicht-kommerzielle Nutzung.

<p align="center">
  <a href="https://ko-fi.com/viewitde">
    <img src="https://ko-fi.com/img/githubbutton_sm.svg" alt="Ko-fi Support"/>
  </a>
</p>
