#!/bin/bash
echo "📊 Estado de todos los servicios:"
echo "=========================================="
docker compose -f docker-compose.yaml ps
echo ""
echo "📈 Uso de recursos:"
docker stats --no-stream
