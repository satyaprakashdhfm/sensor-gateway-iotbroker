import time
import random
import logging
from opcua import Client
from opcua import ua

# Configure logging for our application
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Suppress natural logs from the OPC UA library
logging.getLogger("opcua").setLevel(logging.CRITICAL)

# OPC UA server settings (Container 2)
OPCUA_SERVER_URL = "opc.tcp://container2-gateway:4840"  # Container name from opcua.yml
NAMESPACE = "SENSOR_DATA"  # Simplified namespace

# Sensor configuration
TEMP_MIN = 20.0
TEMP_MAX = 35.0
PRESS_MIN = 995.0
PRESS_MAX = 1025.0
SAMPLE_INTERVAL = 30  # seconds

def generate_sensor_data():
    """Generate random temperature and pressure values."""
    temperature = round(random.uniform(TEMP_MIN, TEMP_MAX), 2)
    pressure = round(random.uniform(PRESS_MIN, PRESS_MAX), 2)
    return temperature, pressure

def main():
    # Initialize OPC UA client
    client = Client(OPCUA_SERVER_URL)

    # Connection retry loop
    connected = False
    while not connected:
        try:
            logger.info(f"[OPC UA CONNECT] Connecting to server at {OPCUA_SERVER_URL}")
            client.connect()
            connected = True
            logger.info("[OPC UA CONNECT] Connection established successfully")
        except Exception as e:
            logger.error(f"[OPC UA CONNECT] Connection failed: {e}")
            logger.info("[OPC UA CONNECT] Retrying in 10 seconds...")
            time.sleep(10)

    try:
        # Get the namespace index
        nsidx = client.get_namespace_index(NAMESPACE)
        logger.info(f"[NAMESPACE] '{NAMESPACE}' resolved with index {nsidx}")

        # Get the node objects
        temp_node = client.get_node(f"ns={nsidx};s=Temperature")
        press_node = client.get_node(f"ns={nsidx};s=Pressure")

        logger.info("[DATA LOOP] Starting sensor data generation loop")

        # Main loop to generate and send sensor data
        while True:
            try:
                # Generate sensor data
                temp, press = generate_sensor_data()

                # Write sensor values to the OPC UA server
                temp_node.set_value(ua.DataValue(ua.Variant(temp, ua.VariantType.Float)))
                press_node.set_value(ua.DataValue(ua.Variant(press, ua.VariantType.Float)))

                logger.info(f"[DATA SENT] Temperature: {temp}°C, Pressure: {press} hPa")

                # Wait for the specified interval before next transmission
                time.sleep(SAMPLE_INTERVAL)

            except Exception as e:
                logger.error(f"[DATA ERROR] Error during data transmission: {e}")
                # Check if the underlying connection is lost and attempt reconnection
                if not client.uaclient._uasocket.is_open():
                    logger.error("[RECONNECT] Connection lost, attempting to reconnect...")
                    client.disconnect()
                    time.sleep(5)
                    client.connect()
                    logger.info("[RECONNECT] Reconnected to OPC UA server successfully")

    except Exception as e:
        logger.error(f"[GENERAL ERROR] {e}")

    finally:
        # Disconnect the OPC UA client if connected
        if connected:
            client.disconnect()
            logger.info("[DISCONNECT] Disconnected from OPC UA server")

if __name__ == "__main__":
    main()
