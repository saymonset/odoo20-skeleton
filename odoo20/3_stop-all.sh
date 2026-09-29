#!/bin/bash
echo "🛑 Apagando todos los servicios..."
docker compose -f docker-compose.yaml down
echo "✅ Todos los servicios apagados"
