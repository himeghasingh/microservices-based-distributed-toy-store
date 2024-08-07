FROM python:3.8-slim
WORKDIR /spring24-lab2-spring24-lab2-tanayjoshi2k-himeghasingh/src/frontend
RUN pip install --no-cache-dir requests
COPY ./frontend/frontend.py /spring24-lab2-spring24-lab2-tanayjoshi2k-himeghasingh/src/frontend/frontend.py
EXPOSE 8003
CMD ["python","-u","./frontend.py"]