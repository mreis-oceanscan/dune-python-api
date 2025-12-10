"""
Usage:           python servo_control.py <host> <port> <servo_name> <value>
Arguments:
    host        - JSONBus server hostname (default: localhost)
    port        - JSONBus server port (default: 9005)
    servo_name  - Name or ID of the servo to control
    value       - Position value in radians (default: 0.0)
"""

import sys
from petinga import VehicleController

host = sys.argv[1]
port = int(sys.argv[2])
servo_name = sys.argv[3]
servo_id = int(servo_name) if servo_name.isdigit() else servo_name
value = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0

controller = VehicleController(host, port)

try:
    print(f"Connecting to vehicle at {host}:{port}...")
    system_name = controller.connect()
    if not system_name:
        print("Warning: Could not determine system name, messages will use default source")
    controller.set_servo_position(servo_id, value)
            
except ConnectionRefusedError:
    print(f"Error: Could not connect to {host}:{port}")
    sys.exit(1)

except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)

finally:
    controller.close()