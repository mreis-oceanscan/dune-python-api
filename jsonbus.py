#!/usr/bin/env python3

import json
import asyncio
from typing import Callable, Optional
from functools import wraps

def require_connection(func):
    '''Decorator that checks if client is connected before executing method.'''
    
    if asyncio.iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(self, *args, **kwargs):
            if self._writer is None or self.system_name is None:
                print(f"Not connected to server. Cannot call {func.__name__}")
                return None
            
            if self._writer.is_closing():
                print(f"Connection closed. Cannot call {func.__name__}")
                return None

            return await func(self, *args, **kwargs)
        return async_wrapper
    else:
        @wraps(func)
        def sync_wrapper(self, *args, **kwargs):
            if self._writer is None or self.system_name is None:
                print(f"Not connected to server. Cannot call {func.__name__}")
                return None
            
            if self._writer.is_closing():
                print(f"Connection closed. Cannot call {func.__name__}")
                return None

            return func(self, *args, **kwargs)
        return sync_wrapper

class JSONBusClient:
    '''Client for DUNE JSONBus transport.'''
    
    def __init__(self, host: str = "localhost", port: int = 9005):
        self.host = host
        self.port = port
        self.system_name = None

        self.listen_timeout = 0.1  # seconds

        self._listen_task = None
        self._listening = False
        self._callbacks = []            # List of (callback, filter) tuples
        self._periodic_tasks = []       # List of (task, interval) tuples

        self._reader = None
        self._writer = None
        self._message_buffer = []
    
    async def connect(self) -> str:
        '''
        Connect to the JSONBus server asynchronously and return the system name.
        '''
        self._reader, self._writer = await asyncio.open_connection(self.host, self.port)
        
        # Read welcome message to get system name
        try:
            welcome_data = await asyncio.wait_for(self._reader.read(4096), timeout=5.0)
            welcome = welcome_data.decode('utf-8')
            welcome_json = json.loads(welcome.strip())
            print(welcome_json)
            self.system_name = welcome_json.get("system_name")
            print(f"Connected to system: {self.system_name}")
        except json.JSONDecodeError as e:
            print(f"Connected but failed to parse welcome: {e}")
            self.system_name = None
        except asyncio.TimeoutError:
            print("Timeout waiting for welcome message")
            self.system_name = None
        
        return self.system_name
    
    async def close(self) -> None:
        '''Close the connection.'''
        
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
            self._writer = None
            self._reader = None
            print("Connection closed")
    
    @require_connection
    async def send(self, message: dict, use_system_src: bool = True) -> None:
        '''
        Send a single JSON message to the JSONBus server.
        
        Args:
            message: The IMC message as a dictionary
            use_system_src: If True, set src to the connected system name
        '''
        if use_system_src and self.system_name and "src" not in message:
            message["src"] = self.system_name
        
        json_str = json.dumps(message) + "\n"
        self._writer.write(json_str.encode('utf-8'))
        await self._writer.drain()

    @require_connection
    async def receive(self) -> Optional[dict]:
        '''
        Receive a single JSON message from the server asynchronously (non-blocking).
        
        Returns:
            Parsed JSON message as dictionary, or None if no message available
        '''
        try:
            # Check if we have buffered messages
            if self._message_buffer:
                return self._message_buffer.pop(0)
            
            # Read data asynchronously with timeout
            data = await asyncio.wait_for(self._reader.read(4096), timeout=self.listen_timeout)
            
            if not data:
                return None
            
            decoded = data.decode('utf-8')
            lines = decoded.strip().split('\n')
            
            # Parse all messages and buffer them
            for line in lines:
                if line:
                    try:
                        msg = json.loads(line)
                        self._message_buffer.append(msg)
                    except json.JSONDecodeError as e:
                        print(f"Failed to decode JSON: {e}")
                        continue
            
            # Return first message if any
            if self._message_buffer:
                return self._message_buffer.pop(0)
                
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            print(f"Error receiving message: {e}")
            return None
        
        return None

    @require_connection
    async def subscribe(self, messages: list[str] = None) -> None:
        '''Subscribe to messages from the server.'''

        if messages:
            await self.send({"command": "subscribe", "messages": messages}, use_system_src=False)
        else:
            await self.send({"command": "subscribe_all"}, use_system_src=False)

    @require_connection
    async def unsubscribe(self) -> None:
        '''Unsubscribe from all messages.'''

        await self.send({"command": "unsubscribe"}, use_system_src=False)

    async def _callback_loop(self) -> None:
        '''
        Single central loop that receives messages and distributes them to all registered callbacks.
        This prevents multiple tasks from trying to read from the same stream.
        '''
        while self._listening:
            try:
                # Receive one message
                msg = await self.receive()
                
                if msg:
                    # Distribute to all callbacks that match the filter
                    for callback, msg_filter in self._callbacks:
                        # Apply filter if specified
                        if msg_filter is None or msg.get("abbrev") in msg_filter:
                            # Support both sync and async callbacks
                            if asyncio.iscoroutinefunction(callback):
                                await callback(msg)
                            else:
                                callback(msg)
                
            except Exception as e:
                print(f"Error in message distribution loop: {e}")
                break

    def start_listening(self) -> None:
        '''
        Internal method to start the message distribution loop.
        Called automatically by run().
        '''
        if not self._listening:
            self._listening = True
            self._listen_task = asyncio.create_task(self._callback_loop())
            print("Started listening for messages...")

    def stop_listening(self) -> None:
        '''
        Stop the message distribution loop.
        '''
        if self._listening:
            self._listening = False
            if self._listen_task:
                self._listen_task.cancel()
                self._listen_task = None
            print("Stopped listening...")

    def add_callback(self, callback: Callable, messages: list[str]) -> None:
        '''
        Register a callback function for specific message types.
        Call this method before run() to set up your message handlers.
        
        Args:
            callback: Function to call when matching messages arrive
            messages: List of messages to receive (e.g., ["EstimatedState"])
        
        Example:
            client = JSONBusClient()
            client.add_callback(onEstimatedState, ["EstimatedState"])
            client.add_callback(onMagneticField, ["MagneticField"])
            client.run()
        '''
        if not callable(callback):
            raise ValueError("callback must be a callable function")

        if not isinstance(messages, list) or not all(isinstance(m, str) for m in messages):
            raise ValueError("messages must be a list of valid message names")        

        self._callbacks.append((callback, messages))
        print(f"Added callback for messages: {messages}")

    def add_periodic_task(self, task: Callable, interval: float) -> None:
        '''
        Register a periodic task to be run at specified intervals.
        
        Args:
            task: Asynchronous function to call periodically
            interval: Time in seconds between calls
        
        Example:
            async def my_periodic_task():
                print("This runs every 5 seconds")
            
            client = JSONBusClient()
            client.add_periodic_task(my_periodic_task, 5.0)
            client.run()
        '''
        if not asyncio.iscoroutinefunction(task):
            raise ValueError("task must be an asynchronous function")
        
        self._periodic_tasks.append((task, interval))
        print(f"Registered periodic task with interval: {interval} seconds")

    async def _run_periodic_task(self, task, interval: float):
        '''Run a periodic task at the specified interval.'''
        while self._listening:
            try:
                await task()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in periodic task: {e}")
    
    def run(self) -> None:
        '''
        Connect to server, subscribe to all registered message types, and start listening.
        This is a blocking call that runs until interrupted (Ctrl+C).
        
        Example:
            client = JSONBusClient(host="localhost", port=9005)
            client.add_callback(my_callback, ["EstimatedState"])
            client.run()  # Blocks here until Ctrl+C
        '''
        async def _run_async():
            try:
                # Connect
                await self.connect()
                
                # Collect all unique message types from callbacks
                all_messages = set()
                for _, msg_filter in self._callbacks:
                    if msg_filter:
                        all_messages.update(msg_filter)
                
                # Subscribe to all message types
                if all_messages:
                    await self.subscribe(list(all_messages))
                    print(f"Subscribed to: {list(all_messages)}")
                
                # Start the callback loop
                self.start_listening()
                
                # Start periodic tasks
                periodic_task_handles = []
                for task, interval in self._periodic_tasks:
                    task_handle = asyncio.create_task(self._run_periodic_task(task, interval))
                    periodic_task_handles.append(task_handle)
                
                if self._periodic_tasks:
                    print(f"Started {len(self._periodic_tasks)} periodic task(s)")
                                
                print("\nListening for subscribed messages... (Press Ctrl+C to stop)\n")
                
                # Keep running until interrupted
                while self._listening:
                    await asyncio.sleep(1)
                    
            except KeyboardInterrupt:
                print("\n\nStopping...")
            finally:

                # Clean up
                self.stop_listening()
                
                # Cancel periodic tasks
                for task_handle in periodic_task_handles:
                    task_handle.cancel()
                
                # Wait for tasks to finish
                if periodic_task_handles:
                    await asyncio.gather(*periodic_task_handles, return_exceptions=True)

                await self.unsubscribe()
                await self.close()
        
        # Run the async event loop
        asyncio.run(_run_async())

