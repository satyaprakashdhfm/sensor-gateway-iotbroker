import time
import logging
import json
from opcua import Server
import paho.mqtt.client as mqtt
import socket
import threading

# Configure logging with detailed output for our own logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Suppress natural logs from imported libraries by setting their log level to CRITICAL
logging.getLogger("opcua").setLevel(logging.CRITICAL)
logging.getLogger("paho").setLevel(logging.CRITICAL)

# OPC UA server settings
SERVER_ENDPOINT = "opc.tcp://0.0.0.0:4840"
SERVER_NAME = "OPC UA Gateway Server"
NAMESPACE = "SENSOR_DATA"

# MQTT settings
MQTT_BROKER = "mqtt-broker"  # Use Docker service name or direct IP if needed
MQTT_PORT = 1883
MQTT_TOPIC = "sensor/data"
MQTT_CLIENT_ID = "opcua_mqtt_gateway"

# Threshold to detect significant sensor change (adjust as needed)
THRESHOLD = 0.001

# Global flag to indicate MQTT connection status
mqtt_connected = False

def on_connect(client, userdata, flags, rc, properties=None):
    global mqtt_connected
    if rc == 0:
        mqtt_connected = True
        logger.info(f"[MQTT CONNECT] Successfully connected to MQTT broker at {resolved_broker}:{MQTT_PORT}")
    else:
        logger.warning(f"[MQTT CONNECT] Connection failed with return code: {rc}")

def on_disconnect(client, userdata, rc, properties=None):
    global mqtt_connected
    mqtt_connected = False
    if rc != 0:
        logger.warning(f"[MQTT DISCONNECT] Unexpected disconnection from MQTT broker (rc={rc})")
    else:
        logger.info("[MQTT DISCONNECT] Disconnected from MQTT broker gracefully.")

def create_mqtt_client():
    client = mqtt.Client(client_id=MQTT_CLIENT_ID, clean_session=True, protocol=mqtt.MQTTv311)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    return client

def mqtt_connection_manager(client):
    global mqtt_connected
    # Resolve MQTT_BROKER hostname
    try:
        resolved = socket.gethostbyname(MQTT_BROKER)
        logger.info(f"[MQTT RESOLVE] Resolved broker '{MQTT_BROKER}' to {resolved}")
    except Exception as e:
        logger.warning(f"[MQTT RESOLVE] Failed to resolve broker '{MQTT_BROKER}': {e}")
        resolved = MQTT_BROKER  # Fallback
    global resolved_broker
    resolved_broker = resolved  # Save globally for logging

    # Start the MQTT network loop once
    client.loop_start()
    logger.info("[MQTT LOOP] MQTT network loop started.")

    while True:
        if not mqtt_connected:
            try:
                logger.info(f"[MQTT CONNECT ATTEMPT] Trying to connect to {resolved}:{MQTT_PORT}")
                client.connect(resolved, MQTT_PORT, keepalive=60)
                time.sleep(5)  # Allow time for the on_connect callback
            except Exception as e:
                logger.error(f"[MQTT CONNECT ERROR] MQTT connection attempt failed: {e}")
        time.sleep(10)

def main():
    # ------------------------------
    # Step 1: Start OPC UA Server
    # ------------------------------
    logger.info("[OPC UA SERVER] Initializing OPC UA server for sensor connections...")
    server = Server()
    server.set_endpoint(SERVER_ENDPOINT)
    server.set_server_name(SERVER_NAME)
    nsidx = server.register_namespace(NAMESPACE)
    logger.info(f"[NAMESPACE REGISTRATION] Registered namespace '{NAMESPACE}' with index {nsidx}")
    objects = server.get_objects_node()
    sensors_folder = objects.add_folder(nsidx, "Sensors")
    temp_var = sensors_folder.add_variable(f"ns={nsidx};s=Temperature", "Temperature", 0.0)
    press_var = sensors_folder.add_variable(f"ns={nsidx};s=Pressure", "Pressure", 0.0)
    temp_var.set_writable()
    press_var.set_writable()
    server.start()
    logger.info(f"[OPC UA SERVER] Started successfully at {SERVER_ENDPOINT}")

    # ------------------------------
    # Step 2: Initialize MQTT Client and Start Connection Manager Thread
    # ------------------------------
    mqtt_client = create_mqtt_client()
    mqtt_thread = threading.Thread(target=mqtt_connection_manager, args=(mqtt_client,), daemon=True)
    mqtt_thread.start()
    logger.info("[MQTT THREAD] MQTT connection manager thread started.")

    # ------------------------------
    # Step 3: Main Loop - Publish Only When Sensor Values Change
    # ------------------------------
    last_temp = None
    last_press = None

    try:
        while True:
            # Read sensor values from OPC UA server
            temp = temp_var.get_value()
            press = press_var.get_value()
            logger.info(f"[SENSOR DATA] Read OPC UA values - Temperature: {temp}°C, Pressure: {press} hPa")

            # Only publish if values have changed beyond the defined threshold
            publish_update = False
            if last_temp is None or abs(temp - last_temp) > THRESHOLD:
                publish_update = True
            if last_press is None or abs(press - last_press) > THRESHOLD:
                publish_update = True

            if publish_update:
                # Update last known values
                last_temp = temp
                last_press = press

                # Publish sensor data if MQTT is connected
                if mqtt_connected:
                    payload = json.dumps({"temperature": temp, "pressure": press})
                    result = mqtt_client.publish(MQTT_TOPIC, payload)
                    if result.rc == mqtt.MQTT_ERR_SUCCESS:
                        logger.info(f"[MQTT PUBLISH] Published payload to topic '{MQTT_TOPIC}': {payload}")
                    else:
                        logger.warning(f"[MQTT PUBLISH ERROR] Failed to publish payload, result code: {result.rc}")
                else:
                    logger.info("[MQTT PUBLISH] MQTT not connected; skipping publish for this cycle.")
            else:
                logger.debug("[SENSOR DATA] No significant change detected; publish skipped.")

            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("[SHUTDOWN] KeyboardInterrupt received. Initiating shutdown sequence.")
    finally:
        try:
            mqtt_client.loop_stop()
            if mqtt_client.is_connected():
                mqtt_client.disconnect()
                logger.info("[MQTT DISCONNECT] MQTT client disconnected successfully.")
        except Exception as e:
            logger.error(f"[MQTT DISCONNECT ERROR] Error during MQTT disconnect: {e}")
        try:
            server.stop()
            logger.info("[OPC UA SERVER] OPC UA server stopped successfully.")
        except Exception as e:
            logger.error(f"[OPC UA STOP ERROR] Error stopping OPC UA server: {e}")

if __name__ == "__main__":
    main()
