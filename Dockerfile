# ── Base image ────────────────────────────────────────────────────────────────
FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    libsndfile1-dev \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Auto-accept Coqui license terms
ENV COQUI_TOS_AGREED=1

# Upgrade pip
RUN pip install --upgrade pip

# Step 1: Pin PyTorch to 2.5.1 — last version before weights_only=True default change
RUN pip install --no-cache-dir \
    "torch==2.5.1" \
    "torchaudio==2.5.1" \
    --index-url https://download.pytorch.org/whl/cpu

# Step 2: Pin transformers to version compatible with Coqui XTTS-v2
# (4.41+ removed BeamSearchScorer)
RUN pip install --no-cache-dir "transformers==4.40.2"

# Step 3: Install TTS and Flask
RUN pip install --no-cache-dir TTS flask

# Copy app
COPY app.py .

RUN mkdir -p outputs

EXPOSE 5000

CMD ["python", "app.py"]