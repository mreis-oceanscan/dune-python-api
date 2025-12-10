#!/usr/bin/env python3

import socket
import json
import time
import math

def require_connection(func):
    '''Decorator that checks if client is connected before executing method.'''

    def wrapper(self, *args, **kwargs):
        if self.sock is None or self.system_name is None:
            print(f"Not connected to server. Cannot call {func.__name__}")
            return
        
        try:
            self.sock.getpeername()[0]
        except:
            print(f"Could not get peer name. Not connected to server. Cannot call {func.__name__}")
            return ''

        return func(self, *args, **kwargs)
    return wrapper

class JSONBusClient:
    '''Client for DUNE JSONBus transport.'''
    
    def __init__(self, host: str = "localhost", port: int = 9005):
        self.host = host
        self.port = port
        self.sock = None
        self.system_name = None
    
    def connect(self) -> str:
        '''Connect to the JSONBus server and return the system name.'''

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.sock.settimeout(5.0)
        
        # Read welcome message to get system name
        welcome = self.sock.recv(4096).decode('utf-8')
        try:
            welcome_json = json.loads(welcome.strip())
            print(welcome_json)
            self.system_name = welcome_json.get("system_name")
            print(f"Connected to system: {self.system_name}")
        except json.JSONDecodeError:
            print(f"Connected: {welcome.strip()}")
            self.system_name = None
        
        return self.system_name
    
    def close(self) -> None:
        ''' Close the connection. '''
        
        if self.sock:
            self.sock.close()
            self.sock = None
            print("Connection closed")
    
    @require_connection
    def send_message(self, message: dict, use_system_src: bool = True) -> None:
        '''
        Send a JSON message to the JSONBus server.
        
        Args:
            message: The IMC message as a dictionary
            use_system_src: If True, set src to the connected system name
        '''
        if use_system_src and self.system_name and "src" not in message:
            message["src"] = self.system_name
        
        json_str = json.dumps(message) + "\n"


        self.sock.sendall(json_str.encode('utf-8'))

    @require_connection
    def subscribe(self, messages: list[str] = None) -> None:
        ''' Subscribe to messages from the server. '''

        if messages:
            self.send_message({"command": "subscribe", "messages": messages}, use_system_src=False)
        else:
            self.send_message({"command": "subscribe_all"}, use_system_src=False)

    @require_connection
    def unsubscribe(self) -> None:
        ''' Unsubscribe from all messages. '''

        self.send_message({"command": "unsubscribe"}, use_system_src=False)

class VehicleController(JSONBusClient):
    '''Controller using JSONBusClient connection.'''
    
    def __init__(self, host: str = "localhost", port: int = 9005):
        super().__init__(host, port)

        self.num_fins = 8

        '''Define servo ID mappings.'''
        self.id_fins = {
                        "port":            1, 
                        "starboard":       2, 
                        "up":              3, 
                        "down":            0,
                        "front_port":      5, 
                        "rear_port":       7, 
                        "front_starboard": 4, 
                        "rear_starboard":  6,
                        }
        
        self.fin_excursion = math.pi/4      # radians
        self.max_speed = 2.0                # m/s

        messages = [ "EstimatedState",
                     "SetServoPosition" ]
        self.subscribe(messages)

    def get_servo_id(self, name) -> int:
        ''' Get servo ID mapping. '''

        if isinstance(name, int):
            if name < 0 or name >= self.num_fins:
                print(f"servo_id must be between 0 and {self.num_fins - 1}")
                return -1
            return name

        elif isinstance(name, str):
            name = name.lower()
            if name in self.id_fins:
                return self.id_fins[name]
        
        print(f"Unknown servo name: {name}")
        return -1
    
    def set_speed(self, speed: float, units: str = "rpm") -> bool:
        ''' Sets the vehicle RPM. '''

        msg = { "abbrev": "DesiredSpeed",
                "value": speed          ,
                "speed_units": units     }
        
        self.send_message(msg)
        print(f"DesiredSpeed: value={speed:.1f} {units} (src={self.system_name})")

    def set_servo_position(self, servo_name, value: float) -> bool:
        ''' Sets the position of a single servo. '''

        servo_id = self.get_servo_id(servo_name)
        if servo_id == -1:
            print(f"Invalid servo name: {servo_name}")
            return False

        msg = { "abbrev": "DesiredServoPosition",
                "id":      servo_id         ,
                "position":   value             }

        self.send_message(msg)
        print(f"DesiredServoPosition: id={servo_id}, pos={value:.3f} (src={self.system_name})")

    def stop(self) -> None:
        ''' Stops the vehicle by setting speed to zero and centering all servos. '''

        for id in range(self.num_fins):
            self.set_servo_position(id, 0.0)
