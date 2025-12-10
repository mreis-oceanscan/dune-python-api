#!/usr/bin/env python3
"""
Example demonstrating multiple callbacks for different message types.
One callback handles EstimatedState messages, another handles MagneticField messages.
"""

import asyncio
from turtle import delay
from jsonbus import JSONBusClient

# Callback for EstimatedState messages
def onEstimatedState(msg):
    """
    Process EstimatedState messages (vehicle position and orientation).
    """
    lat = msg.get('lat', 'N/A')
    lon = msg.get('lon', 'N/A')
    depth = msg.get('depth', 'N/A')
    
    print(f"[EstimatedState] Lat: {lat}, Lon: {lon}, Depth: {depth}m")


# Callback for MagneticField messages
def onSimulatedState(msg):
    """
    Process MagneticField messages (magnetic field readings).
    """
    x = msg.get('x', 'N/A')
    y = msg.get('y', 'N/A')
    z = msg.get('z', 'N/A')
    
    print(f"[SimulatedState] X: {x}, Y: {y}, Z: {z}")

interval = 0.1  # seconds between commands

async def periodic():
    print(f"Task has run...")
        
# Create client
client = JSONBusClient(host="localhost", port=9005)

# Add callbacks for different message types
client.add_callback(onEstimatedState, ["EstimatedState"])
client.add_callback(onSimulatedState, ["SimulatedState"])
client.add_periodic_task(periodic, interval=5.0)            # every 5 seconds

# Run the client (blocks until Ctrl+C)
client.run()