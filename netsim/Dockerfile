FROM python:3.12-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends iproute2 \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir grpcio grpcio-tools protobuf
WORKDIR /app
COPY proto/payload.proto proto/payload.proto
RUN python -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. proto/payload.proto
COPY app/ /app/
RUN chmod +x /app/*.sh