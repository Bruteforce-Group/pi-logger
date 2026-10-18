# Use ARM-compatible Python base (works on Pi OS 64-bit)
FROM python:3.14-slim

# Minimal OS deps for building the spidev Python module
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3-dev build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python deps: spidev for raw SPI access
RUN pip install --no-cache-dir spidev

# App code
WORKDIR /app
COPY app/ /app/

CMD ["python", "-u", "shunt_logger.py"]
