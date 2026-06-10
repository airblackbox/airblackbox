FROM golang:1.25-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
COPY bench/loadgen ./bench/loadgen
RUN CGO_ENABLED=0 go build -o /loadgen ./bench/loadgen

FROM alpine:3.20
COPY --from=builder /loadgen /usr/local/bin/loadgen
ENTRYPOINT ["sh", "-c", "loadgen -baseline http://mockllm:9100 -target http://gateway:8080 -requests ${REQUESTS:-2000} -concurrency ${CONCURRENCY:-1,8,32} -warmup ${WARMUP:-200} -out /results/results.json"]
