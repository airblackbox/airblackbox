# ============================================================================
# This builds the Go GATEWAY, not the MCP server.
#
# Deploying THIS image to the air-mcp Fly app takes mcp.airblackbox.ai down:
# the gateway listens on 8080, the app expects 8085, health checks fail.
# It happened once. The MCP server builds from deploy/mcp/Dockerfile, and a
# bare `fly deploy` from the repo root now does the right thing via the
# root fly.toml - never deploy this file to Fly by hand.
# ============================================================================
FROM golang:1.25-alpine AS builder

RUN apk add --no-cache git

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 go build -o /gateway ./cmd/gateway
RUN CGO_ENABLED=0 go build -o /replayctl ./cmd/replayctl
RUN CGO_ENABLED=0 go build -o /evidencectl ./cmd/evidencectl

FROM alpine:3.21
RUN apk add --no-cache ca-certificates
COPY --from=builder /gateway /usr/local/bin/gateway
COPY --from=builder /replayctl /usr/local/bin/replayctl
COPY --from=builder /evidencectl /usr/local/bin/evidencectl

EXPOSE 8080
ENTRYPOINT ["gateway"]
