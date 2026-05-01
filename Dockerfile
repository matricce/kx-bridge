FROM python:3.11-slim

WORKDIR /app

COPY bridge/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bridge/kobrax_moonraker_bridge.py .
COPY bridge/config_loader.py .
COPY bridge/env_loader.py .
COPY bridge/kobrax_client.py .
COPY VERSION .
COPY bridge/anycubic_slicer.crt .
COPY bridge/anycubic_slicer.key .
COPY bridge/config/config.ini.example /app/config/config.ini.example

# config/ ist ein Volume-Mountpoint – beim Start wird config.ini aus .env migriert
# falls noch keine config.ini vorhanden ist.
RUN mkdir -p /app/config

EXPOSE 7125

ENTRYPOINT ["python", "kobrax_moonraker_bridge.py"]
