import http.server
import json
import requests
import os
from collections import OrderedDict
from threading import Timer
import time

# Define environment variables for service endpoints
FRONTEND_HOST = os.getenv('FRONTEND_HOST', 'localhost')
FRONTEND_PORT = int(os.getenv('FRONTEND_LISTENING_PORT', 8003))

CATALOG_HOST = os.getenv('CATALOG_HOST', 'localhost')
CATALOG_PORT = int(os.getenv('CATALOG_LISTENING_PORT', 8001))

ORDER_HOST = os.getenv('ORDER_HOST', 'localhost')
ORDER_PORT = int(os.getenv('ORDER_LISTENING_PORT', 8002))

# Define a cache for caching product details
cache = OrderedDict()
CACHE_CAPACITY = 7
MAX_PRIORITY = 0
PRIORITIES = {
    1: 8010,
    2: 8011,
    3: 8012
}

# To enable caching, this flag must be set to 1. It can be set to 0 to test performance degrade without caching.
CACHINGFLAG = 1

# Function to check the heartbeat status of the leader


def check_heartbeat_status(host, port):
    global MAX_PRIORITY
    global ORDER_PORT
    headers = {
        'X-Heartbeat-Timestamp': str(int(time.time())),
        'X-Heartbeat-TTL': '3'  # Set TTL to 3 seconds
    }
    print("\n**************************Checking heartbeat for port: ", port, "******************************")
    try:
        response = requests.get(f"http://{host}:{port}/check_heartbeat")
        # Log response from heartbeat status check
        print("\nresponse from check heartbeatstatus for port", port)
        if response.status_code == 200:
            print("Heartbeat received from LEADER node.", port)
    except Exception as e:
        # Log any exception occurred during the heartbeat check
        print(
            f"Failed to receive heartbeat from {port}. Status code: {response.status_code}")
    return response

# Function to conduct leader election
def conduct_election(MAX_PRIORITY, ORDER_PORT):
    print("\nStarting election")
    for priority, port in list(PRIORITIES.items())[::-1]:
        if priority > MAX_PRIORITY:
            try:
                response = check_heartbeat_status(ORDER_HOST, port)
                if response.status_code == 200:
                    MAX_PRIORITY = priority
                    ORDER_PORT = port
                    # Log priority and order port after conducting the election
                    print("\nPriority and order port in conduct election",
                          priority, "  ", ORDER_PORT)
                    notify_followers(ORDER_PORT)
                    return ORDER_PORT
            except Exception as e:
                # Log error if the port is not available during leader election
                print("Trying another port..., logging error: ", e,
                      " ,because port not available", port)
                print("Port ", port, " not available. Logging error: ",
                      e, " Trying another port...")

# Function to periodically check the leader's heartbeat and conduct re-election if necessary
def periodic_leader_check():
    global ORDER_HOST
    global ORDER_PORT
    global MAX_PRIORITY
    print("Periodic leader check, Checking leader heartbeat...", ORDER_PORT)
    try:
        response = check_heartbeat_status(ORDER_HOST, ORDER_PORT)
        if response.status_code != 200:
            MAX_PRIORITY = 0
            print(
                "Leader {ORDER_PORT} is unresponsive, conducting re-election...")
            ORDER_PORT = conduct_election(MAX_PRIORITY, ORDER_PORT)
            if ORDER_PORT is None:
                print("No available leaders, check system status!")
                print(
                    "All order replicas are unresponsive. Exiting the frontend server.")
                os._exit(0)
            else:
                print(f"-------------**************NEW LEADER ELECTED ON PORT {ORDER_PORT} -------------**************")
    except Exception as e:
        MAX_PRIORITY = 0
        print(f"--------###############Leader PORT {ORDER_PORT} died...###############-------------")
        ORDER_PORT = conduct_election(MAX_PRIORITY, ORDER_PORT)
        print("elected order port from except part of periodic leader check", ORDER_PORT)
        if ORDER_PORT is None:
            print("No available leaders, check system status!")
            print("All order replicas are unresponsive. Exiting the frontend server.")
            os._exit(0)
        else:
            print(f"-------------**************NEW LEADER ELECTED ON PORT {ORDER_PORT} -------------**************")

# Function to notify followers about the leader

# Function to notify followers about the leader


def notify_followers(LEADER_ORDER_PORT):
    headers = {
        'X-Heartbeat-Timestamp': str(int(time.time())),
        'X-Heartbeat-TTL': '3'  # Set TTL to 3 seconds
    }
    print("Notifying other replicas about new leader")
    try:
        for port in PRIORITIES.values():
            follower_order_address = f"http://{ORDER_HOST}:{port}/accept_leader_info"
            response = requests.post(follower_order_address, json={
                                     "leader": str(LEADER_ORDER_PORT)}, headers=headers)
            # Log response from notifying followers
            print("Response from notify followers:", response)
        catalog_address = f"http://{CATALOG_HOST}:{CATALOG_PORT}/accept_leader_info"
        response = requests.post(catalog_address, json={
                                 "leader": str(LEADER_ORDER_PORT)}, headers=headers)
    except Exception as e:
        # Log error if the port is not available during notification
        print("Port is not available", port)

# Conduct initial leader election
ORDER_PORT = conduct_election(MAX_PRIORITY, ORDER_PORT)
print("LEADER_ORDER_PORT", ORDER_PORT)

class FEService(http.server.BaseHTTPRequestHandler):

    # Function to evict the least recently used item from the cache
    def evict_lru(self):
        if len(cache) > CACHE_CAPACITY:
            cache.popitem(last=False)
            # Log final cache status after eviction
            print("\nFinal cache status", cache)

    # Function to retrieve product details from the Catalog service
    def get_product_details(self, product_name):
        url = f"http://{CATALOG_HOST}:{CATALOG_PORT}/products/{product_name}"
        # Send a GET request to the catalog service
        response = requests.get(url)
        # Log response from the catalog service
        print("RESPONSE", response)
        return response  # Return the response object

    # Function to retrieve order details from the Order service
    def get_order_details(self, order_number):
        # Construct URL for retrieving order details from the order service
        url = f"http://{ORDER_HOST}:{ORDER_PORT}/orders/{order_number}"
        response = requests.get(url)  # Send GET request to order service
        return response

    # Function to place an order through the Order service
    def place_order(self, order_data):
        url = f"http://{ORDER_HOST}:{ORDER_PORT}/orders"
        headers = {'Content-type': 'application/json'}
        response = requests.post(url, json=order_data, headers=headers)
        response_data = response.json()
        return {"status": response.status_code, "data": response_data}

    # Handle GET requests
    def do_GET(self):

        if self.path.startswith("/send_leader_info"):
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            leader_info = f"Leader Order Port: {ORDER_PORT}"
            self.wfile.write(leader_info.encode('utf-8'))

        if self.path.startswith("/products"):
            product_name = self.path.split("/")[-1]
            if CACHINGFLAG:
                if product_name in cache:
                    print(f"\nServing {product_name} from cache...", cache)
                    qty = cache[product_name]
                    response_data = {"name": product_name, "qty": qty}
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(response_data).encode('utf-8'))
                    cache.move_to_end(product_name)
                    print("\nFinal cache status", cache)
                else:
                    print("\nCache Miss", cache)
                    response = self.get_product_details(product_name)
                    status_code = response.status_code
                    if response.status_code == 200:
                        data = response.json()
                        item, qty = data['name'], data['qty']
                        cache[item] = qty
                        print("New Cache Populated", cache)
                        self.evict_lru()
                        self.send_response(status_code)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps(data).encode('utf-8'))
                        cache.move_to_end(item)
                        print("\nFinal cache status", cache)
                    else:
                        product_not_found = {
                            "error": {
                                "code": 404,
                                "message": "Product not found"
                            }
                        }
                        self.send_response(status_code)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps(
                            product_not_found).encode('utf-8'))
            else:
                response = self.get_product_details(product_name)
                status_code = response.status_code
                if response.status_code == 200:
                    data = response.json()
                    item, qty = data['name'], data['qty']
                    self.send_response(status_code)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(data).encode('utf-8'))
                else:
                    product_not_found = {
                        "error": {
                            "code": 404,
                            "message": "Product not found"
                        }
                    }
                    self.send_response(status_code)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(
                        product_not_found).encode('utf-8'))

        if self.path.startswith("/orders"):
            # Extract order number from the path
            order_number = self.path.split("/")[-1]
            response = self.get_order_details(
                order_number)  # Get order details
            self.send_response(response.status_code)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response.json()).encode('utf-8'))

    # Handle POST requests
    def do_POST(self):
        if self.path.startswith("/orders"):
            content_length = int(self.headers['Content-Length'])
            order_data = self.rfile.read(content_length).decode('utf-8')
            order_data = json.loads(order_data)
            print("Order Data", order_data, "\n")
            response_data = self.place_order(order_data)
            print("Response Data", response_data, "\n")
            self.send_response(response_data["status"])
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data["data"]).encode('utf-8'))

    # Handle DELETE requests
    def get_product_details(self, product_name):
        try:
            url = f"http://{CATALOG_HOST}:{CATALOG_PORT}/products/{product_name}"
            print("\n---------------------Trying to get product details from catalog for : ", product_name, "---------------------")
            # Send a GET request to the catalog service
            response = requests.get(url)
            print("\n---------------------Response received for get product details for: ", product_name, " : ", response.json(), "---------------------")
            return response  # Return the response object
        except Exception as e:
            print(f"Error in get_product_details: {e}")
            return {"status": 500, "data": {"error": "Internal Server Error"}}

    def get_order_details(self, order_number):
        try:
            # Construct URL for retrieving order details from the order service
            url = f"http://{ORDER_HOST}:{ORDER_PORT}/orders/{order_number}"
            print("\n---------------------Trying to fetch order details from catalog for : ", order_number, "---------------------")
            response = requests.get(url)  # Send GET request to order service
            print("\n---------------------Response received for fetch order details for: ", order_number, " : ", response.json(), "---------------------")

            return response
        except Exception as e:
            print(f"Error in get_order_details: {e}")
            return {"status": 500, "data": {"error": "Internal Server Error"}}

    def place_order(self, order_data):
        try:
            print("\n---------------------Trying to place order for : ", order_data, "---------------------")
            url = f"http://{ORDER_HOST}:{ORDER_PORT}/orders"
            headers = {'Content-type': 'application/json'}
            response = requests.post(url, json=order_data, headers=headers)
            response_data = response.json()
            print("\n---------------------Response received for place order details for: ", order_data, " : ", response_data, "---------------------")
            return {"status": response.status_code, "data": response_data}
        except Exception as e:
            print(f"Error in place_order: {e}")
            return {"status": 500, "data": {"error": "Internal Server Error"}}

    def do_DELETE(self):
        if self.path.startswith("/delete"):
            item = self.path.split("/")[-1]
            if item in cache:
                print(f"Invalidating {item} from cache...\n")
                del cache[item]
                print("Cache after deletion", cache)
                print("\n")
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response_data = {"message": f"Item {item} deleted from cache"}
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
            else:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                error_data = {"error": {"code": 404,
                                        "message": "Item not found in cache"}}
                self.wfile.write(json.dumps(error_data).encode('utf-8'))
        else:
            self.send_response(400)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            response = "Bad Request: Invalid endpoint"
            self.wfile.write(response.encode('utf-8'))

# Function to periodically check the leader's status


def check():
    periodic_leader_check()
    Timer(3.0, check).start()


check()

# Function to run the HTTP server


def run(server_class=http.server.ThreadingHTTPServer, handler_class=FEService, port=FRONTEND_PORT):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Front End Service running on port {port}")
    httpd.serve_forever()


if __name__ == "__main__":
    run()
