#!/bin/bash

# Source environment variables from .env file
. .env

# Directory where the order service script is located
ORDER_DIR="./order"

python3.9 "$ORDER_DIR/order.py" $ORDER_PORT_2 $ORDER_PRIORITY_2 &