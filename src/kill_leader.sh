#!/bin/bash
. .env
# Check for processes listening on order port 3
lsof -i :$ORDER_PORT_3

# Extract the PID of the process listening on order port 3
PID=$(lsof -i :$ORDER_PORT_3 | awk 'NR==2 {print $2}')

# Kill the process using the extracted PID
if [ -n "$PID" ]; then
    echo "Killing process with PID $PID..."
    kill -9 $PID
else
    echo "No process found listening on port 8012."
fi
