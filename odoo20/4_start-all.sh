#!/bin/bash
echo "🚀 Iniciando todos los servicios..."
docker compose -f docker-compose.yaml up -d
echo "✅ Servicios iniciados"
echo ""
echo "Estado de los servicios:"
docker compose -f docker-compose.yaml ps
