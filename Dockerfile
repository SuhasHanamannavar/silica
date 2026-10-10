FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip verilator yosys build-essential make ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*
RUN pip3 install --no-cache-dir huggingface_hub
WORKDIR /app
COPY . /app
ENV PORT=8000 HF_TOKEN="" SILICA_HF_MODEL="Qwen/Qwen2.5-Coder-7B-Instruct"
EXPOSE 8000
CMD ["python3", "server.py"]
