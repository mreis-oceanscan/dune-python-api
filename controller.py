import math
import asyncio
from jsonbus import JSONBusClient


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
    
    async def set_speed(self, speed: float, units: str = "rpm") -> bool:
        ''' Sets the vehicle RPM. '''

        msg = { "abbrev": "DesiredSpeed",
                "value": speed          ,
                "speed_units": units     }
        
        await self.send(msg)
        print(f"DesiredSpeed: value={speed:.1f} {units} (src={self.system_name})")

    async def set_servo_position(self, servo_name, value: float) -> bool:
        ''' Sets the position of a single servo. '''

        servo_id = self.get_servo_id(servo_name)
        if servo_id == -1:
            print(f"Invalid servo name: {servo_name}")
            return False

        msg = { "abbrev": "DesiredServoPosition",
                "id":      servo_id         ,
                "position":   value             }

        await self.send(msg)
        print(f"DesiredServoPosition: id={servo_id}, pos={value:.3f} (src={self.system_name})")

    async def stop(self) -> None:
        ''' Stops the vehicle by setting speed to zero and centering all servos. '''

        for id in range(self.num_fins):
            await self.set_servo_position(id, 0.0)
