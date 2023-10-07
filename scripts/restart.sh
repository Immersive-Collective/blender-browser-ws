#!/bin/bash

# Fetch the PID for the process using port 8765
PID=$(lsof -ti :8765)

# If a PID was found, kill the process
if [ -n "$PID" ]; then
    kill -9 $PID
fi

# Start Blender with the specified file and window size
/Applications/Blender.app/Contents/MacOS/Blender /Users/smielniczuk/Documents/works/ic/blender-browser-ws/blender/test_cube_rotation.blend -p 0 0 980 1080

