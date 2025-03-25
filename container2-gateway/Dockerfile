FROM python:3.9-slim

WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir opcua paho-mqtt

# Copy gateway script
COPY gateway_as_opcua_server.py .

# Run the gateway script
CMD ["python", "gateway_as_opcua_server.py"]
