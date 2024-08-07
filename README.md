# Toy Store Simulation Project

## Features

- **Learn about Caching, Replication, and Consistency:** Understand how caching mechanisms, data replication strategies, and consistency models work in distributed systems.
- **Explore Fault Tolerance and High Availability:** Gain insights into ensuring system reliability and availability, even in the face of failures.
- **Deploy Your Application on the Cloud:** Discover how to containerize and deploy your application using Docker and Docker Compose.
- **Optionally Learn about Paxos and Raft:** Explore distributed consensus algorithms like Paxos and Raft for handling leader election and achieving consensus in distributed systems.

## Overview

This project simulates interactions with an online toy store server. It includes a client script, frontend, order backend, and catalog service, all designed to handle product queries and order placements efficiently. The system is containerized using Docker for consistency and scalability.

## Client

The client script simulates interactions with the toy store server. It handles connection persistence, product queries, and order placements based on predefined probabilities.

### Features

- **Connection Handling:** Maintains a persistent connection using the `Connection: keep-alive` header.
- **Order Placement:** Calculates the number of orders to place based on probability and total requests, randomly selects items, and places orders via POST requests.
- **Error Handling:** Retries requests up to three times if the leader node dies.
- **Testing:** Conducted with 5 clients sending 20 requests each, with probabilities varying from 0 to 1.

### Details

- **GET Requests:** Retrieves product information from the frontend.
- **POST Requests:** Places orders if the item's quantity is positive.
- **Order Logging:** Logs successful orders in a CSV file and handles order retrieval if probability is non-zero.
- **Retries:** Retries failed requests three times with a 2-second interval.

## Frontend

The frontend service routes requests between clients and backend services, maintains a cache, and handles leader election for order services.

### Features

- **Request Routing:** Routes GET requests to the Catalog service and POST requests to the Order service.
- **Cache Management:** Implements an LRU eviction policy with a cache capacity of 7 toys.
- **Leader Election:** Conducts leader election and periodic leader checks to ensure service availability.

### Method Definitions

- `do_GET`: Routes GET requests to the Catalog service.
- `do_POST`: Routes POST requests to the Order service.
- `get_product_details`: Handles GET request responses.
- `place_order`: Handles POST request responses.
- `get_session_id`: Retrieves Session-ID from request headers.
- `check_heartbeat_status`: Checks leader availability.
- `conduct_election`: Elects a new leader if necessary.
- `periodic_leader_check`: Periodically checks leader status and re-conducts elections if needed.
- `evict_lru`: Manages the LRU cache eviction policy.
- `do_DELETE`: Deletes/invalidate items from the cache.

## Order Backend

The Order service handles order placements and ensures consistency across replicas.

### Features

- **Order Processing:** Receives POST requests from the frontend, decrements item quantity, and maintains order logs.
- **Replication:** Writes logs to ensure consistency across order replicas.
- **Missed Orders Handling:** Requests missing logs from the leader if an order replica has missed any orders.

### Method Definitions

- `do_POST`: Handles POST requests, processes orders, and maintains logs.
- `send_order_data`: Sends log rows to other replicas.
- `get_leader_info`: Retrieves the leader's port number.
- `get_missed_orders`: Requests missing logs from the leader.
- `find_order`: Compares client logs with order service logs.
- `do_GET`: Handles GET requests for order validation.

## Catalog Service

The Catalog service manages product information, processes orders, and maintains inventory.

### Features

- **Order Processing:** Deducts item quantities based on order requests.
- **Restocking:** Restocks items to 100 if out of stock.
- **Cache Invalidation:** Sends invalidation requests to the frontend for updated inventory.

### Method Definitions

- `do_GET`: Handles GET requests for product information.
- `do_POST`: Handles POST requests for placing orders.
- `restock`: Restocks out-of-stock items and invalidates cache.
- `schedule_restock`: Schedules periodic restocking every 10 seconds.

## Communication

All services communicate using REST APIs. The system relies on well-defined API endpoints for interactions between services, frontend, and clients.

## Containerization

### Docker Setup

The entire system is containerized using Docker. Each component (client, frontend, order backend, and catalog service) is encapsulated in its own Docker container to ensure consistency and ease of deployment.

### Dockerfile Examples

#### Client

The client Dockerfile sets up the environment for running the client script:

```dockerfile
# Client Dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY client_script.py /app/

RUN pip install requests

CMD ["python", "client_script.py"]
