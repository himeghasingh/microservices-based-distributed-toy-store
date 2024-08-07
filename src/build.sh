#!/bin/bash

# Stop execution if any command fails
set -e

# Create the network if it doesn't already exist
if ! docker network ls | grep -qw tanmeg-network; then
  docker network create tanmeg-network
fi

# Check if the frontend-container exists, if yes, stop and remove it
if [ "$(docker ps -aq -f name=^frontend-container$)" ]; then
    docker stop frontend-container
    docker rm frontend-container
fi

# Check if the catalog-container exists, if yes, stop and remove it
if [ "$(docker ps -aq -f name=^catalog-container$)" ]; then
    docker stop catalog-container
    docker rm catalog-container
fi

# Check if the order-container exists, if yes, stop and remove it
if [ "$(docker ps -aq -f name=^order-container$)" ]; then
    docker stop order-container
    docker rm order-container
fi

# # To run as individual builds and runs with Dockerfiles

# # Build images with no cache
# docker build --no-cache -f frontend.Dockerfile -t frontend-image .
# docker build --no-cache -f catalog.Dockerfile -t catalog-image .
# docker build --no-cache -f order.Dockerfile -t order-image .


# # Run containers
# docker run -d --network my_network --name frontend-container -p 8003:8003 -e FRONTEND_HOST=frontend-container -e FRONTEND_PORT=8003 -e CATALOG_HOST=catalog-container -e CATALOG_PORT=8001 -e ORDER_HOST=order-container -e ORDER_PORT=8002 frontend-image

# docker run -d --network my_network --name catalog-container -p 8001:8001 -e CATALOG_HOST=catalog-container -e CATALOG_PORT=8001 -v "$(pwd)/catalog/data:/spring24-lab2-spring24-lab2-tanayjoshi2k-himeghasingh/src/catalog/data" catalog-image

# docker run -d --network my_network --name order-container -p 8002:8002 -e ORDER_HOST=order-container -e ORDER_PORT=8002 -e CATALOG_HOST=catalog-container -e CATALOG_PORT=8001 -v "$(pwd)/order/data:/spring24-lab2-spring24-lab2-tanayjoshi2k-himeghasingh/src/order/data" order-image

# To run as docker-compose
docker-compose up --build