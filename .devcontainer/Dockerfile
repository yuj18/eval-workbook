# syntax=docker/dockerfile:1
FROM continuumio/miniconda3:latest

# Set environment variable to avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies first
RUN apt-get update && apt-get install -y \
    git \
    sudo \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd --create-home --shell /bin/bash vscode \
    && usermod -aG sudo vscode \
    && echo 'vscode ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# Initialize conda for the vscode user
RUN echo ". /opt/conda/etc/profile.d/conda.sh" >> /home/vscode/.bashrc \
    && echo "conda activate base" >> /home/vscode/.bashrc

# Set workdir
WORKDIR /workspaces/eval

# Switch to non-root user
USER vscode
