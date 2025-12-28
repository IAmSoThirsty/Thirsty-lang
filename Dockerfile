# Thirsty-lang Docker Image
# Multi-stage build for optimal image size

FROM node:20-alpine AS node-base

# Install Python
RUN apk add --no-cache python3 py3-pip bash

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install Node.js dependencies
RUN npm ci --only=production

# Copy Python requirements
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt || true

# Copy source code
COPY . .

# Make scripts executable
RUN chmod +x quickstart.sh setup_venv.sh

# Create a non-root user
RUN addgroup -g 1001 thirsty && \
    adduser -D -u 1001 -G thirsty thirsty && \
    chown -R thirsty:thirsty /app

USER thirsty

# Expose port for web playground
EXPOSE 8080

# Default command: show help
CMD ["node", "src/thirsty-cli.js", "--help"]

# --- Development Stage ---
FROM node-base AS development

USER root

# Install development dependencies
COPY requirements-dev.txt ./
RUN pip3 install --no-cache-dir -r requirements-dev.txt || true

# Install Node.js dev dependencies
RUN npm install

USER thirsty

# Development mode with volume mounting
CMD ["npm", "run", "repl"]
