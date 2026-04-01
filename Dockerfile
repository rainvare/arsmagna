FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application code
COPY . .
RUN chmod +x start.sh

# Hugging Face Spaces expects port 7860
EXPOSE 7860

# Start with the pipeline script
CMD ["bash", "start.sh"]
