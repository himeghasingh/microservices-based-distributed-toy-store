#!/bin/bash

# Source environment variables from .env file
. .env

# Directory where the order service script is located
ORDER_DIR="./order"

# Start three instances of the order service with different ports and priorities
# Each instance runs in the background (&) to allow for concurrent execution
python3.9 "$ORDER_DIR/order.py" $ORDER_PORT_1 $ORDER_PRIORITY_1 &
python3.9 "$ORDER_DIR/order.py" $ORDER_PORT_2 $ORDER_PRIORITY_2 &
python3.9 "$ORDER_DIR/order.py" $ORDER_PORT_3 $ORDER_PRIORITY_3 &
