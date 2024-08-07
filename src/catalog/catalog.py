import http.server
import json 
import requests
from threading import Lock, Timer
import os 
import csv 

# Define environment variables for service endpoints
FRONTEND_HOST = os.getenv('FRONTEND_HOST', 'localhost')
FRONTEND_PORT = int(os.getenv('FRONTEND_LISTENING_PORT', 8003))

CATALOG_HOST = os.getenv('CATALOG_HOST', 'localhost')
CATALOG_PORT = int(os.getenv('CATALOG_LISTENING_PORT', 8001))

ORDER_HOST = os.getenv('ORDER_HOST', 'localhost')
ORDER_PORT = int(os.getenv('ORDER_LISTENING_PORT', 8002))

# Define a lock for thread safety
lock = Lock()

# Function to load items from a CSV file
def load_items():
    items = {}
    # Open the CSV file containing item details
    with open("./data/data.csv", "r") as f:
        # Skip the header line
        next(f)
        # Iterate over each line in the CSV file
        for item in f:
            # Split the line by commas to extract item details
            name, qty, cost = item.strip("\n").split(",")
            # Store the item details in a dictionary
            items[name] = {
                "qty": int(qty),
                "cost": float(cost)
            }
    return items

# Function to restock items if quantity is below a threshold
def restock():
    # Print current status of items in the catalog
    print("Status of items in catalog:", items)
    # Flag to track if restocking is required
    restock_flag = False
    # Iterate over each item in the catalog
    for item, details in items.items():
        # If quantity of an item is below or equal to 0, restocking is required
        if details['qty'] <= 0:
            restock_flag = True
            # Reset quantity to a default value
            items[item]['qty'] = 100
            # Invalidate cache for the restocked item
            DELETE_URL = f"http://{FRONTEND_HOST}:{FRONTEND_PORT}/delete/{item}"
            requests.delete(DELETE_URL) 
    # If restocking occurred, update the CSV file and print restocked items
    if restock_flag:
        update_items_csv(items)
        print("\nRestocked items: ", items)

# Function to update the CSV file with item details
def update_items_csv(items):
    with open("./data/data.csv", "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Name', 'Quantity', 'Cost']) 
        for name, details in items.items():
            writer.writerow([name, details['qty'], details['cost']])

# Load items from CSV into memory
items = load_items()

# Define the Catalog server handler
class CatalogServer(http.server.BaseHTTPRequestHandler):

    # Handle POST requests
    def do_POST(self):
        if self.path.startswith("/accept_leader_info"):
            # Extract and parse JSON data from request body
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8')) 
            # If 'leader' key is present in JSON data, update ORDER_PORT
            if 'leader' in data:
                global ORDER_PORT
                ORDER_PORT = data['leader']
                # Send a 200 OK response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response_data = {"message": "Received leader information successfully"}
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
            else:
                # If 'leader' key is missing, send a 400 Bad Request response
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                error_data = {"error": {"code": 400, "message": "Missing 'leader' in JSON data"}}
                self.wfile.write(json.dumps(error_data).encode('utf-8'))

        if self.path.startswith("/decrement_stock"):
            # Extract item name from URL
            item_name = self.path.split("/")[-1]
            # Check if item exists in catalog
            if item_name in items:
                with lock:
                    # Extract and parse JSON data from request body
                    content_length = int(self.headers['Content-Length']) 
                    order_data = self.rfile.read(content_length).decode('utf-8')
                    order_data = json.loads(order_data)
                    req_qty = order_data['qty']
                    available_qty = items[item_name]['qty']
                    # Check if requested quantity is available
                    if available_qty > 0 and req_qty <= available_qty:
                        # Decrement item quantity
                        items[item_name]['qty'] -= req_qty
                        # Update CSV file with new item details
                        update_items_csv(items)
                        # Send a 200 OK response
                        self.send_response(200) 
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        response_data = {"message": "Stock decremented successfully"}
                        self.wfile.write(json.dumps(response_data).encode('utf-8'))
                        # Invalidate cache for the decremented item
                        DELETE_URL = f"http://{FRONTEND_HOST}:{FRONTEND_PORT}/delete/{item_name}"
                        res = requests.delete(DELETE_URL) 
                    else:
                        # If requested quantity exceeds available quantity, send a 400 Bad Request response
                        print("Insufficient Quantity")
                        self.send_response(400) 
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        error_data = {"error": {"code": 400, "message": "Insufficient quantity available"}}
                        self.wfile.write(json.dumps(error_data).encode('utf-8'))
            else:
                # If item does not exist in catalog, send a 404 Not Found response
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                error_data = {"error": {"code": 404, "message": "Invalid toy name"}}
                self.wfile.write(json.dumps(error_data).encode('utf-8'))

    # Handle GET requests
    def do_GET(self):
        if self.path.startswith("/products"):
            # Extract item name from URL
            item_name = self.path.split("/")[-1]
            # Check if item exists in catalog
            if item_name in items:
                with lock:
                    # Retrieve item information from catalog
                    product_info = items[item_name]
                    # Construct response data with item details
                    response_data = {
                        "name": item_name,
                        "qty": product_info["qty"],
                        "cost": product_info["cost"]
                    }
                # Send a 200 OK response with item details
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
            else:
                # If item does not exist in catalog, send a 404 Not Found response
                error_data = {
                    "error": {
                        "code": 404,
                        "message": "Product not found"
                    }
                }
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(error_data).encode('utf-8'))
        else:
            # If requested URL does not match any endpoint, send a 404 Not Found response
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            response = "Page Not Found!"
            self.wfile.write(response.encode('utf-8'))
        
# Function to schedule restocking at regular intervals
def schedule_restock():
    restock()
    # Schedule the next restocking after 10 seconds
    Timer(10.0, schedule_restock).start()

# Start the restocking schedule
schedule_restock()

# Function to run the HTTP server
def run(server_class=http.server.ThreadingHTTPServer, handler_class=CatalogServer, port=CATALOG_PORT):
    # Create an HTTP server instance with the specified handler class and port
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    # Print a message indicating the server is running
    print(f"Server running on port {port}")
    # Start the HTTP server to handle incoming requests indefinitely
    httpd.serve_forever()

# Entry point of the script
if __name__ == "__main__":
    # Start the HTTP server
    run()
