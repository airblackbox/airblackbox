# AIR Blackbox Gateway — Deploy Commands
#
# Usage:
#   make up        Start the full stack
#   make down      Stop everything
#   make status    Check what's running
#   make logs      Tail gateway logs
#   make comply    Run compliance check
#   make demo      Generate demo data and check compliance
#   make clean     Remove all data volumes

COMPOSE_BASE = docker compose -f ../docker-compose.yaml
COMPOSE_FULL = $(COMPOSE_BASE) -f docker-compose.full.yaml

.PHONY: up down status logs comply demo clean

up:
	@echo "Starting AIR Blackbox full stack..."
	$(COMPOSE_FULL) up -d
	@echo ""
	@echo "Services:"
	@echo "  Gateway:    http://localhost:8080"
	@echo "  Jaeger UI:  http://localhost:16686"
	@echo "  MinIO:      http://localhost:9001"
	@echo "  Prometheus: http://localhost:9091"
	@echo ""
	@echo "Run: air-blackbox comply -v"

down:
	$(COMPOSE_FULL) down

status:
	$(COMPOSE_FULL) ps

logs:
	$(COMPOSE_FULL) logs -f gateway

comply:
	air-blackbox comply -v

demo:
	air-blackbox demo
	air-blackbox comply -v

clean:
	$(COMPOSE_FULL) down -v
	@echo "All data volumes removed."
