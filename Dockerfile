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
