# Thirsty-lang Docker Image
# Production-ready container for running Thirsty-lang

FROM node:20-slim

# Install Python3
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install Node.js dependencies (if any)
RUN npm ci --only=production || true

# Copy Python requirements
COPY requirements.txt ./
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt || true

# Copy source code
COPY . .

# Make scripts executable
RUN chmod +x quickstart.sh setup_venv.sh src/*.py 2>/dev/null || true

# Create a non-root user
RUN useradd -m -u 1001 thirsty && \
    chown -R thirsty:thirsty /app

USER thirsty

# Expose port for web playground
EXPOSE 8080

# Default command: show help
CMD ["node", "src/thirsty-cli.js", "--help"]

# --- Development Stage ---
FROM node:20-slim AS development

# Install Python and development tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-pip git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy all files
COPY . .

# Install dependencies
RUN npm install && \
    pip3 install --no-cache-dir --break-system-packages -r requirements-dev.txt || true

# Make scripts executable
RUN chmod +x quickstart.sh setup_venv.sh src/*.py 2>/dev/null || true

# Development mode with volume mounting
CMD ["npm", "run", "repl"]
