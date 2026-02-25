# ── Base image ────────────────────────────────────────────────────────────────
FROM python:3.11-slim

# System dependencies for audio processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    libsndfile1-dev \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Auto-accept Coqui license terms (required for non-interactive/Docker use)
ENV COQUI_TOS_AGREED=1

# Upgrade pip first
RUN pip install --upgrade pip

# Step 1: Install PyTorch CPU (avoids hash issues by using official index)
RUN pip install --no-cache-dir \
    torch \
    torchaudio \
    --index-url https://download.pytorch.org/whl/cpu

# Step 2: Pin transformers to version compatible with Coqui TTS XTTS-v2
# (transformers 4.41+ removed BeamSearchScorer which TTS depends on)
RUN pip install --no-cache-dir "transformers==4.40.2"

# Step 3: Install TTS and Flask
RUN pip install --no-cache-dir TTS flask

# Copy app
COPY app.py .

# Create output directory
RUN mkdir -p outputs

EXPOSE 5000

CMD ["python", "app.py"]