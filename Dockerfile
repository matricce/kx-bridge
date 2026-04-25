FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt

COPY kobrax_moonraker_bridge.py .
COPY env_loader.py .
COPY kobrax_client.py .
COPY anycubic_slicer.crt .
COPY anycubic_slicer.key .

EXPOSE 7125

ENTRYPOINT ["python", "kobrax_moonraker_bridge.py"]
