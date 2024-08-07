import http.server
import json
import requests
from threading import Lock
import os
import sys

FRONTEND_HOST = os.getenv('ORDER_HOST', 'localhost')
FRONTEND_PORT = int(os.getenv('FRONTEND_LISTENING_PORT', 8003))

CATALOG_HOST = os.getenv('CATALOG_HOST', 'localhost')
CATALOG_PORT = int(os.getenv('CATALOG_LISTENING_PORT', 8001))

ORDER_HOST = os.getenv('ORDER_HOST', 'localhost')
ORDER_PORT = int(sys.argv[1])
LEADER_ORDER_PORT = None

REPLICA_NUMBER = int(sys.argv[2])
ORDER_PORTS = [8010, 8011, 8012]

def send_order_data(host, port, order_data):
    url = f"http://{host}:{port}/replicate_order"
    response = requests.post(url, data=order_data)
    return response

def get_leader_info(ORDER_HOST, ORDER_PORT):
    url = f"http://{ORDER_HOST}:{ORDER_PORT}/send_leader_info"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            leader_info = response.text
            leader_port = int(leader_info.split(":")[-1].strip())
            return leader_port
        else:
            return None
    except Exception as e:
        return None

def get_missed_orders(latest_order_number, ORDER_HOST, LEADER_ORDER_PORT):
    try:
        url = f"http://{ORDER_HOST}:{LEADER_ORDER_PORT}/missed_orders/{latest_order_number}"
        response = requests.get(url)
        if response.status_code == 200:
            missed_orders = json.loads(response.content)
            return missed_orders
        else:
            return None 
    except Exception as e:
        return None 

class OrderService(http.server.BaseHTTPRequestHandler):
    global LEADER_ORDER_PORT
    global ORDER_HOST
    global ORDER_PORT
    global FRONTEND_HOST
    
    latest_order_number = order_number = -1
    file_name = f"./order/data/order_data_{REPLICA_NUMBER}.csv"
    orders_data_list = []

    if os.path.exists(file_name):
        with open(file_name, "r") as f:
            data = f.readlines()
            if data:
                order = data[-1].split(",")[0]
                order_number = int(order.split(":")[1])
                latest_order_number = order_number
       
    else:
        with open(file_name, "w") as f:
            pass

    lock = Lock()
    try:
        NEW_LEADER_PORT = get_leader_info(FRONTEND_HOST, FRONTEND_PORT)
        if NEW_LEADER_PORT:
            LEADER_ORDER_PORT = NEW_LEADER_PORT
        if LEADER_ORDER_PORT:
            missed_orders = get_missed_orders(latest_order_number, ORDER_HOST, LEADER_ORDER_PORT)
            if missed_orders:
                if os.path.exists(file_name):
                    with open(file_name, "a") as f:
                        for idx in missed_orders:
                            f.write(f"{missed_orders[idx]}\n")
                        print("Fetched missed orders for port : ", ORDER_PORT)
    except Exception as e:
        print("Frontend Service not running yet", e)

    def do_GET(self):
        global LEADER_ORDER_PORT
        if self.path.startswith("/check_heartbeat"):
            try:
            # Order service is alive
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Leader is alive.".encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write("Leader is not responsive.".encode('utf-8'))

        if "missed_orders" in self.path:
            try:
                latest_order_number = int(self.path.split("/")[-1])
                missed_orders = self.orders_data_list[latest_order_number + 1:]
                missed_orders_dict = {}

                for i, missed_order in enumerate(missed_orders):
                    missed_orders_dict[i] = missed_order
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(missed_orders_dict).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write("Internal Server Error".encode('utf-8'))

        if self.path.startswith("/orders"):
            order_number = int(self.path.split("/")[-1])
            order_info = self.find_order(order_number)
            if order_info:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(order_info).encode('utf-8'))
            else:
                error_message = {
                    "error": {
                        "code": 404,
                        "message": "Order not found"
                    }
                }
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(error_message).encode('utf-8'))

    def do_POST(self):
        global LEADER_ORDER_PORT
        global ORDER_PORT

        if self.path.startswith("/accept_leader_info"):
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            if 'leader' in data:
                LEADER_ORDER_PORT = data['leader']
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response_data = {
                    "message": "Received leader information successfully"}
                self.wfile.write(json.dumps(response_data).encode('utf-8'))

            else:
                # If 'leader' key is missing, send a 400 Bad Request response
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                error_data = {"error": {"code": 400,
                                        "message": "Missing 'leader' in JSON data"}}
                self.wfile.write(json.dumps(error_data).encode('utf-8'))

        if self.path.startswith("/replicate_order"):
            try:
                content_length = int(self.headers['Content-Length'])
                order_data = self.rfile.read(content_length).decode('utf-8')
                OrderService.order_number = int(order_data.split(":")[1].split(",")[0])
                self.orders_data_list.append(order_data)
                with open(self.file_name, 'a') as f:
                    f.write(f"{order_data}\n")

                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Wrote data to replica".encode('utf-8'))
            except Exception as e:
                print("Replication: Cannot write to dead node")

        if self.path.startswith("/orders"):
            content_length = int(self.headers['Content-Length'])
            order_data = self.rfile.read(content_length).decode('utf-8')
            order_data = json.loads(order_data)
            name, qty = order_data['name'], order_data['qty']
            url = f"http://{CATALOG_HOST}:{CATALOG_PORT}/decrement_stock/{name}"
            response = requests.post(url, json=order_data)
            status_code = response.status_code

            if status_code == 200:
                with OrderService.lock:
                    OrderService.order_number += 1
                    order_placed = {
                        "data": {
                            "order_number": OrderService.order_number
                        }
                    }
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(order_placed).encode('utf-8'))
                    order_data = f"number: {OrderService.order_number}, name: {name}, qty: {qty}"
                    self.orders_data_list.append(order_data)
                    with open(self.file_name, 'a') as f:
                        f.write(f"{order_data}\n")

                    for port in ORDER_PORTS:
                        if port != int(LEADER_ORDER_PORT):
                            try:
                                response = send_order_data(ORDER_HOST, port, order_data)
                            except Exception as e:
                                print("LEADER: Cannot write to dead node.")

            elif status_code == 400:
                error_message = {
                    "error": {
                        "code": 400,
                        "message": "Insufficient quantity available"
                    }
                }
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(error_message).encode('utf-8'))
            elif status_code == 404:
                error_message = {
                    "error": {
                        "code": 404,
                        "message": "Invalid toy name"
                    }
                }
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(error_message).encode('utf-8'))

    def find_order(self, order_number):
        if os.path.exists(self.file_name):
            with open(self.file_name, "r") as f:
                for line in f:
                    order_fields = line.strip().split(",")
                    order_id = int(order_fields[0].split(":")[1].strip())
                    if order_id == order_number:
                        item = order_fields[1].split(":")[1].strip()
                        quantity = int(order_fields[2].split(":")[1].strip())
                        return {
                            "number": order_id,
                            "name": item,
                            "qty": quantity
                        }
        return None

def run(server_class=http.server.ThreadingHTTPServer, handler_class=OrderService, port=ORDER_PORT):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Order Service running on port {port}")
    httpd.serve_forever()

if __name__ == "__main__":
    run()