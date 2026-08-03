# AIR Blackbox governance MCP server - remote connector for claude.ai
# Build from repo root:  docker build -f deploy/mcp/Dockerfile -t air-mcp .
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY sdk/ sdk/
RUN pip install --no-cache-dir ".[mcp,gate,monitor]"

# Records persist here; mount a volume in production.
ENV AIR_RUNS_DIR=/data/runs \
    AIR_MCP_TRANSPORT=http \
    AIR_MCP_PORT=8085
VOLUME /data
EXPOSE 8085

CMD ["air-blackbox-mcp"]
