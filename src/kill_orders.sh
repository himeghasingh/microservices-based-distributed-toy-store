#!/bin/bash
. .env

# Check for processes listening on order ports 1, 2, and 3
lsof -i :$ORDER_PORT_1
lsof -i :$ORDER_PORT_2
lsof -i :$ORDER_PORT_3

# Get the PID of the processes listening on the specified ports
PID_1=$(lsof -i :$ORDER_PORT_1 | awk 'NR==2 {print $2}')
PID_2=$(lsof -i :$ORDER_PORT_2 | awk 'NR==2 {print $2}')
PID_3=$(lsof -i :$ORDER_PORT_3 | awk 'NR==2 {print $2}')

# Kill the processes if they are running
if [ ! -z "$PID_1" ]; then
    echo "Killing process with PID $PID_1 listening on order port 1"
    kill -9 $PID_1
fi

if [ ! -z "$PID_2" ]; then
    echo "Killing process with PID $PID_2 listening on order port 2"
    kill -9 $PID_2
fi

if [ ! -z "$PID_3" ]; then
    echo "Killing process with PID $PID_3 listening on order port 3"
    kill -9 $PID_3
fi
