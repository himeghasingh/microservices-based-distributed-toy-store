import http.client
import json
import random
import os
import time
import csv

import argparse

# Define the frontend service host and port
parser = argparse.ArgumentParser(description="Client for interacting with the frontend service.")
parser.add_argument("--host", type=str, default="localhost", help="Frontend service host")
parser.add_argument("--port", type=int, default=8003, help="Frontend service port")
args = parser.parse_args()

# Update host and port based on command-line arguments
FRONTEND_HOST = args.host
FRONTEND_PORT = args.port

# List of items
items = ["tux", "whale", "fox", "elephant", "dolphin", "monopoly", "lego", "marbles", "frisbee", "bicycle"]

# Lists to store latencies for query and order requests
query_latencies = []
order_latencies = []

# Function to save order information to a CSV file
def save_order_to_csv(order_info, filename):
    with open(filename, 'a', newline='') as csvfile:
        fieldnames = ['number', 'name', 'qty']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if os.stat(filename).st_size == 0:
            writer.writeheader()
        writer.writerow(order_info)

# Function to read orders from a CSV file
def read_orders_from_csv(filename):
    orders = []
    with open(filename, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            orders.append(row['number'])
    return orders

# Function to send HTTP requests
def send_request(method, path, data=None, headers=None, retries=3):
    conn = http.client.HTTPConnection(FRONTEND_HOST, FRONTEND_PORT)
    for _ in range(retries):
        try:
            conn.request(method, path, body=data, headers=headers)
            response = conn.getresponse()
            conn.close()
            return response
        except Exception as e:
            time.sleep(2)
    return None

# Main function to simulate client behavior
def main():
    prob = 0.2  # Probability of placing an order
    total_requests = 20  # Total number of requests
    orders_to_place = int(total_requests * prob)
    order_positions = set(random.sample(range(total_requests), orders_to_place))
    orders_file = f'./data/orders_{os.getpid()}.csv'  # Include process ID in the filename
    
    for i in range(total_requests):
        order_request_flag = 0
        start = time.time()
        product_name = random.choice(items)
        response = send_request("GET", f"/products/{product_name}", headers={'Connection': 'keep-alive'})

        if response:
            status = response.status
            data = response.read().decode('utf-8')
            data = json.loads(data)

            print("GET =>", status, data)

            if status != 404:
                qty = data['qty']
                if qty > 0 and i in order_positions:
                    order_request_flag = 1
                    random_qty = random.randint(1, 5)
                    order_data = json.dumps({"name": product_name, "qty": random_qty})
                    headers = {'Content-type': 'application/json', 'Connection': 'keep-alive'}
                    response = send_request("POST", "/orders", data=order_data, headers=headers)

                    if response:
                        status = response.status
                        data = response.read().decode('utf-8')
                        print("POST =>", status, data)

                        if status == 200:
                            order_number = json.loads(data)["data"]["order_number"]
                            print("Order Number:", order_number)
                            order_info = {'number': order_number, 'name': product_name, 'qty': random_qty}
                            save_order_to_csv(order_info, orders_file)
        end = time.time()
        req_time = end - start
        if order_request_flag:
            order_latencies.append(req_time)
        else:
            query_latencies.append(req_time)

    if prob:
        order_numbers = read_orders_from_csv(orders_file)

        for order_number in order_numbers:
            with open(orders_file, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if row['number'] == order_number:
                        local_order_info = {"number": int(row["number"]), "name": row["name"], "qty": int(row['qty'])}
                        response = send_request("GET", f"/orders/{order_number}", headers={'Connection': 'keep-alive'})
                        status = response.status
                        if response:
                            remote_order_info = json.loads(response.read().decode('utf-8'))
                            print("\n\n-------------------------------------------------------------------")
                            print("Local Order Info =>", local_order_info, type(local_order_info))
                            print("Remote Order Info =>", remote_order_info, type(remote_order_info))
                            if local_order_info == remote_order_info:
                                print(f"Order {order_number}: Data matches")
                            else:
                                print(f"Order {order_number}: Data does not match")
        
    # Calculate average latencies
    avg_query_latency = sum(query_latencies) / len(query_latencies) if query_latencies else 0
    avg_order_latency = sum(order_latencies) / len(order_latencies) if order_latencies else 0
    
    # Print latencies and average latencies
    print("Query latencies:", query_latencies)
    print("Order latencies:", order_latencies)
    print(f"Average query latency: {avg_query_latency:.10f} seconds for client with process ID : ", os.getpid())
    print(f"Average order latency: {avg_order_latency:.10f} seconds for client with process ID : ", os.getpid())
    print("\n\n")
    
# Execute the main function if the script is run directly
if __name__ == "__main__":
    main()
