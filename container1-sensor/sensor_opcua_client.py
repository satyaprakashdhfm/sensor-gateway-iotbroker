import time
import random
import logging
from opcua import Client
from opcua import ua

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
            logger.info(f"Attempting to connect to OPC UA server at {OPCUA_SERVER_URL}")
            client.connect()
            connected = True
            logger.info("Connected to OPC UA server")
        except Exception as e:
            logger.error(f"Failed to connect to OPC UA server: {e}")
            logger.info("Retrying in 10 seconds...")
            time.sleep(10)
    
    try:
        # Get the namespace index
        nsidx = client.get_namespace_index(NAMESPACE)
        logger.info(f"Namespace index for {NAMESPACE}: {nsidx}")
        
        # Get the node objects
        temp_node = client.get_node(f"ns={nsidx};s=Temperature")
        press_node = client.get_node(f"ns={nsidx};s=Pressure")
        
        logger.info("Starting sensor data generation loop")
        
        # Main loop to generate and send data
        while True:
            try:
                # Generate random sensor values
                temp, press = generate_sensor_data()
                
                # Write values to OPC UA server
                temp_node.set_value(ua.DataValue(ua.Variant(temp, ua.VariantType.Float)))
                press_node.set_value(ua.DataValue(ua.Variant(press, ua.VariantType.Float)))
                
                logger.info(f"Sent data - Temperature: {temp}°C, Pressure: {press} hPa")
                
                # Wait for the specified interval
                time.sleep(SAMPLE_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error during data transmission: {e}")
                if not client.uaclient._uasocket.is_open():
                    logger.error("Connection lost. Attempting to reconnect...")
                    client.disconnect()
                    time.sleep(5)
                    client.connect()
                    logger.info("Reconnected to OPC UA server")
    
    except Exception as e:
        logger.error(f"Error: {e}")
    
    finally:
        # Disconnect client
        if connected:
            client.disconnect()
            logger.info("Disconnected from OPC UA server")

if __name__ == "__main__":
    main()
