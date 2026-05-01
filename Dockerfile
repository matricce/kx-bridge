FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY kobrax_moonraker_bridge.py .
COPY config_loader.py .
COPY env_loader.py .
COPY kobrax_client.py .
COPY VERSION .
COPY anycubic_slicer.crt .
COPY anycubic_slicer.key .
COPY config/config.ini.example /app/config/config.ini.example

# config/ ist ein Volume-Mountpoint – beim Start wird config.ini aus .env migriert
# falls noch keine config.ini vorhanden ist.
RUN mkdir -p /app/config

EXPOSE 7125

ENTRYPOINT ["python", "kobrax_moonraker_bridge.py"]
