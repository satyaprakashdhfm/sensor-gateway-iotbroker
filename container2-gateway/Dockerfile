FROM python:3.9-slim

WORKDIR /app

# Install mosquitto-clients and other dependencies
RUN apt-get update && \
    apt-get install -y mosquitto-clients && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir opcua paho-mqtt

# Copy gateway script
COPY gateway_as_opcua_server.py .

# Run the gateway script
CMD ["python", "gateway_as_opcua_server.py"]
