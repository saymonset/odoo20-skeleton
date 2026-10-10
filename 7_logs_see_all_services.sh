#!/bin/bash
echo "📋 Mostrando logs de todos los servicios..."
echo "Presiona Ctrl+C para salir"
docker compose -f docker-compose.yaml logs -f
