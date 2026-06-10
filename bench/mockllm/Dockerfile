FROM golang:1.25-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
COPY bench/mockllm ./bench/mockllm
RUN CGO_ENABLED=0 go build -o /mockllm ./bench/mockllm

FROM alpine:3.20
COPY --from=builder /mockllm /usr/local/bin/mockllm
EXPOSE 9100
ENTRYPOINT ["mockllm"]
