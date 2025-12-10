"""
Swimmer Petinga
Usage:           python swimmer.py <host> <port>
Arguments:
    host        - JSONBus server hostname (default: localhost)
    port        - JSONBus server port (default: 9005)
"""

import sys
import asyncio
from controller import VehicleController

host = sys.argv[1]
port = int(sys.argv[2])

print(f"Connecting to buv-petinga at {host}:{port}...")

controller = VehicleController(host, port)

async def main():
    try:

        system_name = await controller.connect()
        if not system_name:
            print("Warning: Could not determine system name, messages will use default source")

        # Sweep servos 4-7 from -0.7 to 0.7 radians
        start_id = 4
        end_id = 7

        start_value = -0.7
        end_value = 0.7
        increment = 0.1

        delay = 0.1  # seconds between commands
        
        print(f"\nSweeping servos {start_id}-{end_id} from {start_value} to {end_value} rad")
        print("Press Ctrl+C to stop\n")
        
        while True:

            # Sweep forward
            value = start_value
            while value <= end_value:
                for servo_id in range(start_id, end_id + 1):
                    await controller.set_servo_position(servo_id, value)
                await asyncio.sleep(delay)
                value += increment
            
            # Sweep backward
            value = end_value
            while value >= start_value:
                for servo_id in range(start_id, end_id + 1):
                    await controller.set_servo_position(servo_id, value)
                await asyncio.sleep(delay)
                value -= increment
                
    except KeyboardInterrupt:
        print("\nStopped by user")
        await controller.stop()
    except ConnectionRefusedError:
        print(f"Error: Could not connect to {host}:{port}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await controller.close()

if __name__ == "__main__":
    asyncio.run(main())