FROM node:22-alpine

LABEL maintainer="РПК ПинГвин AI Agent"
LABEL description="OpenClaw AI Sales Agent for RPK PinGvin"

# Install OpenClaw globally
RUN npm install -g openclaw@latest

# Set working directory
WORKDIR /app

# Copy workspace (skills, AGENTS.md, SOUL.md, HEARTBEAT.md)
COPY workspace/ /app/workspace/

# Copy OpenClaw config
COPY openclaw.json /root/.openclaw/openclaw.json

# Create directories for uploads and data
RUN mkdir -p /app/uploads /app/data /root/.openclaw

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD openclaw doctor 2>&1 | grep -q "ready" || exit 1

# Expose gateway port
EXPOSE 18789

# Start OpenClaw gateway
CMD ["openclaw", "gateway", "--port", "18789", "--workspace", "/app/workspace"]
