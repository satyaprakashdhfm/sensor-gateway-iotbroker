FROM python:3.9-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir opcua numpy

# Copy sensor script
COPY sensor_opcua_client.py .

# Run the sensor script
CMD ["python", "sensor_opcua_client.py"]
