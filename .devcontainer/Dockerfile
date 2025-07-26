FROM mcr.microsoft.com/devcontainers/python:1-3.11-bullseye

RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install development dependencies
RUN pip install --upgrade pip && \
    pip install pytest httpx[cli] polars[all] sentence-transformers vectorbt ruff black

WORKDIR /workspace