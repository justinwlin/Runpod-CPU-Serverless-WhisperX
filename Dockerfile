# Use an official and specific version tag if possible, instead of 'latest'
FROM runpod/pytorch:2.0.1-py3.10-cuda11.8.0-devel-ubuntu22.04

# Environment variables
ENV PYTHONUNBUFFERED=1 

# Modes can be: pod, serverless
ARG MODE_TO_RUN=pod
ENV MODE_TO_RUN=$MODE_TO_RUN

ARG CONCURRENCY_MODIFIER=1
ENV CONCURRENCY_MODIFIER=$CONCURRENCY_MODIFIER

# Set up the working directory
WORKDIR /app

# Install dependencies in a single RUN command to reduce layers
# Clean up in the same layer to reduce image size
RUN apt-get update --yes --quiet && \
    DEBIAN_FRONTEND=noninteractive apt-get install --yes --quiet --no-install-recommends \
    software-properties-common \
    gpg-agent \
    build-essential \
    apt-utils \
    ca-certificates \
    ffmpeg \
    curl && \
    add-apt-repository --yes ppa:deadsnakes/ppa && \
    apt-get update --yes --quiet && \
    DEBIAN_FRONTEND=noninteractive apt-get install --yes --quiet --no-install-recommends

# Create and activate a Python virtual environment
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Install Python packages
# Install Python packages in a single RUN instruction
RUN pip install --no-cache-dir \
    OhMyRunPod \
    asyncio \
    requests \
    yt-dlp \
    numpy==1.26.4 \
    runpod==1.6.2

# Install requirements.txt
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt
    
# Remove Runpod's copy of start.sh and replace it with our own
RUN rm ../start.sh

# COPY EVERYTHING INTO THE CONTAINER
COPY . .

RUN chmod +x start.sh

# WHISPERX Stuff
RUN pip install --no-cache-dir setuptools-rust==1.8.0 whisperx

# CONFIRM THAT FFMPEG IS INSTALLED
RUN ffmpeg -version

RUN python preload.py

# depot build -t justinwlin/serverlessllm:1.0 . --push --platform linux/amd64
CMD ["/app/start.sh"]