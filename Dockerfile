# syntax=docker/dockerfile:1
FROM golang:1.25-alpine AS builder

RUN apk add --no-cache git

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 go build -o /gateway ./cmd/gateway
RUN CGO_ENABLED=0 go build -o /replayctl ./cmd/replayctl
RUN CGO_ENABLED=0 go build -o /evidencectl ./cmd/evidencectl

FROM python:3.13-alpine

RUN apk add --no-cache ca-certificates supervisor

# Go binaries
COPY --from=builder /gateway /usr/local/bin/gateway
COPY --from=builder /replayctl /usr/local/bin/replayctl
COPY --from=builder /evidencectl /usr/local/bin/evidencectl

# Python dashboard
COPY dashboard/requirements.txt /dashboard/requirements.txt
RUN pip install --no-cache-dir -r /dashboard/requirements.txt

COPY dashboard/ /dashboard/

# Supervisor config: runs both Go proxy and Python dashboard
COPY <<'EOF' /etc/supervisord.conf
[supervisord]
nodaemon=true
logfile=/dev/stdout
logfile_maxbytes=0

[program:gateway]
command=/usr/local/bin/gateway
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:dashboard]
command=uvicorn dashboard.app:app --host 0.0.0.0 --port 8081 --app-dir /
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
environment=RUNS_DIR="%(ENV_RUNS_DIR)s",GATEWAY_URL="http://localhost:8080"
EOF

EXPOSE 8080 8081
ENTRYPOINT ["supervisord", "-c", "/etc/supervisord.conf"]
