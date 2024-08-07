FROM python:3.8-slim
WORKDIR /spring24-lab2-spring24-lab2-tanayjoshi2k-himeghasingh/src/catalog
RUN pip install --no-cache-dir requests
COPY ./catalog/catalog.py /spring24-lab2-spring24-lab2-tanayjoshi2k-himeghasingh/src/catalog/catalog.py
EXPOSE 8001
CMD ["python","-u","./catalog.py"]