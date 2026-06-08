FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY kobrax_moonraker_bridge.py .
COPY web/ ./web/
# Statische Daten (orca_filaments.json etc.) liegen in /app/static/, NICHT in
# /app/data/ — letzteres wird vom User als Volume gemountet (Runtime-State).
COPY data/ ./static/
COPY config_loader.py .
COPY env_loader.py .
COPY kobrax_client.py .
COPY orca_filaments.py .
COPY VERSION .
COPY anycubic_slicer.crt .
COPY anycubic_slicer.key .
COPY config/config.ini.example /app/config/config.ini.example

# config/ ist ein Volume-Mountpoint – beim Start wird config.ini aus .env migriert
# falls noch keine config.ini vorhanden ist.
RUN mkdir -p /app/config && mkdir -p /app/data

# Daten-Verzeichnis fest auf /app/data (sonst würde der Binary-Default <exe-dir>/data greifen)
# und Container-Erkennung für den Bridge-Restart (Supervisor startet neu statt subprocess).
ENV KX_DATA_DIR=/app/data
ENV KX_IN_DOCKER=1

EXPOSE 7125

ENTRYPOINT ["python", "kobrax_moonraker_bridge.py"]
