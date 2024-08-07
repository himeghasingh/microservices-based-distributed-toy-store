# CS 677 Lab 3

## Prerequisites

- Python 3.9.12 installed on your machine.
- In the .env file, update the FRONTEND_HOST, CATALOG_HOST AND ORDER_HOST IP Addresses to the IP of the machine on which your server is running. PORTS can be left untouched.

## Usage

1. **Catalog Service**
   Navigate to the catalog directory of the project and execute:
   
    ```bash
    python3.9 catalog.py
    ```

2. **Order Service**
   Navigate to the src directory of the project and execute:
   
    ```bash
    ./start_orders.sh
    ```

    To kill the leader order replica, which in this case is the replica hosted on port 8012 with highest priority 3, execute:

    ```bash
    ./kill_leader.sh
    ```

    To bring back the above replica alive, execute:

     ```bash
    ./start_leader.sh

    ```
    To kill all the leader order replicas at once, execute:

    ```bash
    ./kill_orders.sh
    ```

3. **Frontend Service**
   Navigate to the frontend directory of the project and execute:
   
    ```bash
    python3.9 frontend.py
    ```

4. **Client**
   Navigate to the client directory of the project and execute:
   
    ```bash
    python3.9 client.py --host <FRONTEND_HOST_IP> --port <FRONTEND_HOST_PORT>
    ```

   The above configuration is assuming that every microservice of the server is on the same machine.

5. **AWS Deployment**
    Refer EvalDocs.pdf for AWS Deployment and Network Configuration.

### Steps to run test suite:
- Run all services - Catalog, Order and Frontend
  
Navigate to /test dir and run

```bash
python3.9 test.py
```
- Note: Running test suite writes the test results to a separate test_logs file.
