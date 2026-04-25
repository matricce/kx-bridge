FROM python:3.11-slim

WORKDIR /app

COPY 05_scripts/requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt

COPY 05_scripts/kobrax_moonraker_bridge.py .
COPY 05_scripts/env_loader.py .
COPY 05_scripts/kobrax_client.py .
COPY 05_scripts/anycubic_slicer.crt .
COPY 05_scripts/anycubic_slicer.key .

EXPOSE 7125

ENTRYPOINT ["python", "kobrax_moonraker_bridge.py"]
