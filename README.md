# DUNE Python API

A Python client library for controlling underwater vehicles through DUNE's JSONBus protocol.

## Project Structure

```
dune-python-api/
├── petinga.py          # Core API classes (JSONBusClient, VehicleController)
├── servo_control.py    # CLI tool for single servo control
├── swimmer.py          # Example: continuous servo sweeping demo
└── README.md           # This file
```

## Requirements

- Python 3.6+
- Access to a DUNE JSONBus server (default port: 9005)

## Quick Start

### Basic Usage

```python
from petinga import VehicleController

# Connect to vehicle
controller = VehicleController(host="localhost", port=9005)
controller.connect()

# Control servos
controller.set_servo_position("port", 0.5)      # By name
controller.set_servo_position(1, 0.5)           # By ID (0-7)

# Set speed
controller.set_speed(1500, units="rpm")

# Emergency stop
controller.stop()

# Disconnect
controller.close()
```

### Available Servo Names

- `port`, `starboard`, `up`, `down`
- `front_port`, `rear_port`, `front_starboard`, `rear_starboard`

## Examples

### Command-Line Tools

**Control a single servo:**
```bash
python servo_control.py localhost 9005 port 0.5
```

**Run swimming demo:**
```bash
python swimmer.py localhost 9005
```
Press `Ctrl+C` to stop.

### Python Script Example

```python
from petinga import VehicleController
import time

controller = VehicleController("192.168.0.100", 9005)

try:
    controller.connect()
    
    # Sweep port fin
    for angle in [-0.5, 0.0, 0.5, 0.0]:
        controller.set_servo_position("port", angle)
        time.sleep(1)
    
    controller.stop()
    
except Exception as e:
    print(f"Error: {e}")
finally:
    controller.close()
```

## License

[Add your license here]

## Contact

Built for OceanScan - Marine Systems & Technology
