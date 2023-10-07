import sys
import os

libs_path = "/Users/smielniczuk/Documents/works/ic/blender-browser-ws/app/libs"
if libs_path not in sys.path:
    sys.path.append(libs_path)

import websockets
import asyncio
import bpy
import threading
import queue


import subprocess


def kill_port(port):
    """Kill process running on the given port, if any"""
    try:
        result = subprocess.check_output(
            f"lsof -n -i :{port} | grep LISTEN", shell=True, universal_newlines=True
        )
        pid = result.split()[1]
        os.kill(int(pid), 9)
    except Exception as e:
        print(f"No process using port {port} or couldn't kill it.")


# Before starting the server
kill_port(8765)


connected_clients = set()  # To track all connected clients

# Queue for sending messages from Blender's main thread to the websocket thread
message_queue = queue.Queue()


async def notify_clients(message):
    """Send a message to all connected clients."""
    if connected_clients:
        await asyncio.wait([client.send(message) for client in connected_clients])


import json


def check_for_new_cube(scene, depsgraph):
    threejs_data = []

    for obj in bpy.data.objects:
        # If we're only interested in certain object types, we can filter them here
        # For this example, we'll focus on MESH and CAMERA types
        if obj.type in ["MESH", "CAMERA"]:
            obj_attributes = {}
            # Extracting location, rotation and scale as they're commonly needed for ThreeJS
            location = obj.location
            rotation = obj.rotation_euler
            scale = obj.scale

            # Convert Blender's Z-up coordinate system to Three.js's Y-up system
            x, y, z = location
            threejs_location = [x, z, -y]

            rx, ry, rz = rotation
            threejs_rotation = [rx, rz, -ry]

            # Scale remains the same for both coordinate systems
            threejs_scale = list(scale)

            threejs_data.append(
                {
                    "name": obj.name,
                    "type": obj.type,
                    "location": threejs_location,
                    "rotation": threejs_rotation,
                    "scale": threejs_scale,
                }
            )

    json_str = json.dumps(threejs_data)
    message_queue.put(json_str)


bpy.app.handlers.depsgraph_update_post.append(check_for_new_cube)


def rotate_cube():
    cube = bpy.data.objects.get("Cube")
    if cube:
        cube.rotation_euler.z += 0.1


async def handle_client(websocket, path):
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            if message == "rotate":
                rotate_cube()
                response = "Cube rotated!"
                await websocket.send(response)
            else:
                response = "Invalid message"
                await websocket.send(response)
    finally:
        connected_clients.remove(websocket)


# Global variable to save the PID
websocket_pid = None


# Modify your websocket_server function:
def websocket_server(stop_event):
    global websocket_pid
    # Store the PID of the current process
    websocket_pid = os.getpid()

    # rest of the function...
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    serve = websockets.serve(handle_client, "localhost", 8765)

    # This task will check for messages in the queue and forward them to clients
    async def forward_messages():
        while not stop_event.is_set():
            while not message_queue.empty():
                message = message_queue.get()
                await notify_clients(message)
            await asyncio.sleep(0.1)

    asyncio.ensure_future(forward_messages())
    loop.run_until_complete(serve)
    loop.run_forever()


stop_event = threading.Event()
thread = threading.Thread(target=websocket_server, args=(stop_event,))


def kill_previous_websocket_server():
    """Kill previous websocket server if it's running."""
    global websocket_pid
    if websocket_pid:
        try:
            os.kill(websocket_pid, 9)
            print(f"Killed previous WebSocket server with PID: {websocket_pid}")
        except ProcessLookupError:
            print("Previous WebSocket server was not running.")


kill_previous_websocket_server()


thread.start()
