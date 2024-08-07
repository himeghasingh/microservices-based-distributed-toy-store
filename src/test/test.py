import unittest
import requests
import json
import os
import sys
import random
import time
import subprocess
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from frontend import frontend

# Load items from data file
items = {}
with open("data.csv", "r") as f:
    next(f)
    data = f.readlines()
    for item in data:
        name, qty, cost = item.strip("\n").split(",")
        items[name] = {
            "qty": int(qty),
            "cost": float(cost)
        }

# Define error messages
product_not_found = {
    "error": {
        "code": 404,
        "message": "Product not found"
    }
}

insufficient_qty = {
    "error": {
        "code": 400,
        "message": "Insufficient quantity available"
    }
}

FRONTEND_HOST = os.getenv('FRONTEND_HOST', 'localhost')
FRONTEND_PORT = int(os.getenv('FRONTEND_LISTENING_PORT', 8003))

CATALOG_HOST = os.getenv('CATALOG_HOST', 'localhost')
CATALOG_PORT = int(os.getenv('CATALOG_LISTENING_PORT', 8001))

ORDER_HOST = os.getenv('ORDER_HOST', 'localhost')
ORDER_PORT = int(os.getenv('ORDER_LISTENING_PORT', 8002))

MAX_PRIORITY = 0
PRIORITIES = {1: 8010, 2: 8011, 3: 8012}

# Conduct election to determine the leader order port
ORDER_PORT = frontend.conduct_election(MAX_PRIORITY, ORDER_PORT)
FRONTEND_URL = f"http://{FRONTEND_HOST}:{FRONTEND_PORT}"
ORDER_URL = f"http://{ORDER_HOST}:{ORDER_PORT}"
CATALOG_URL = f"http://{CATALOG_HOST}:{CATALOG_PORT}"

# Test Catalog Service
class TestCatalogService(unittest.TestCase):

    # Test querying product details successfully
    def test_query_product_catalog_success(self):
        product_name = random.choice(list(items.keys()))
        response = requests.get(f"{CATALOG_URL}/products/{product_name}")
        self.assertEqual(response.status_code, 200)

    # Test querying product details for a non-existent product
    def test_query_product_catalog_fail(self):
        product_name = "cat"  # unavailable product
        response = requests.get(f"{CATALOG_URL}/products/{product_name}")
        response_data = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response_data, product_not_found)

# Test Order Service
class TestOrderService(unittest.TestCase):
    def test_place_order_success(self):
        global ORDER_PORT
        global ORDER_HOST
        ORDER_URL = f"http://{ORDER_HOST}:{ORDER_PORT}"
        product_name = random.choice(list(items.keys()))
        order_data = {
            "name": product_name,
            "qty": 10
        }
        headers = {'Content-type': 'application/json'}
        response = requests.post(f"{ORDER_URL}/orders",
                                 data=json.dumps(order_data), headers=headers)
        self.assertEqual(response.status_code, 200)

    # Test placing an order for a product with insufficient quantity
    def test_place_order_fail(self):
        global ORDER_HOST
        global ORDER_PORT
        ORDER_URL = f"http://{ORDER_HOST}:{ORDER_PORT}"
        product_name = random.choice(list(items.keys()))
        order_data = {
            "name": product_name,
            "qty": 99999999999
        }
        headers = {'Content-type': 'application/json'}

        response = requests.post(f"{ORDER_URL}/orders",
                                 data=json.dumps(order_data), headers=headers)
        response_data = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response_data, insufficient_qty)

# Test the overall service
class TestFrontendService(unittest.TestCase):
    # Test querying product details successfully
    def test_query_product_frontend_success(self):
        product_name = random.choice(list(items.keys()))
        response = requests.get(f"{FRONTEND_URL}/products/{product_name}",
                                headers={'Session-ID': "testsession", 'Connection': 'keep-alive'})
        self.assertEqual(response.status_code, 200)

    # Test querying product details for a non-existent product
    def test_query_product_frontend_fail(self):
        name = "cat"  # unavailable product
        response = requests.get(f"{FRONTEND_URL}/products/{name}",
                                headers={'Session-ID': "testsession", 'Connection': 'keep-alive'})
        response_data = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response_data, product_not_found)

    # Test placing an order successfully
    def test_buy_product_frontend_sucess(self):
        product_name = random.choice(list(items.keys()))
        order_data = {
            "name": product_name,
            "qty": 10
        }
        headers = {'Content-type': 'application/json',
                   'Session-ID': "testsession", 'Connection': 'keep-alive'}
        response = requests.post(f"{FRONTEND_URL}/orders",
                                 data=json.dumps(order_data), headers=headers)
        self.assertEqual(response.status_code, 200)

    # Test placing an order for a product with insufficient quantity
    def test_buy_product_frontend_fail(self):
        product_name = random.choice(list(items.keys()))
        order_data = {
            "name": product_name,
            "qty": 99999999999
        }
        headers = {'Content-type': 'application/json',
                   'Session-ID': "testsession", 'Connection': 'keep-alive'}
        response = requests.post(f"{FRONTEND_URL}/orders",
                                 data=json.dumps(order_data), headers=headers)
        response_data = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response_data, insufficient_qty)

    # Test leader failure handling
    def test_leader_failure(self):
        global ORDER_PORT
        global ORDER_HOST
        global MAX_PRIORITY
        os.chdir('..')
        subprocess.run(["./kill_leader.sh"], shell=True)
        time.sleep(5)

        # Query the current leader
        response = frontend.check_heartbeat_status(ORDER_HOST, PRIORITIES[2])
        ORDER_PORT = frontend.conduct_election(MAX_PRIORITY, ORDER_PORT)
        # Assert that port 8011 is elected as the new leader
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ORDER_PORT, PRIORITIES[2])

# Run the test suite and write output to a log file
if __name__ == "__main__":
    with open('test_logs', 'w') as f:
        runner = unittest.TextTestRunner(stream=f, verbosity=2)
        unittest.main(testRunner=runner)