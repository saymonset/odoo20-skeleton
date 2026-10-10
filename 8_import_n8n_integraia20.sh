#!/usr/bin/env bash
# 8_import_n8n_integraia20.sh — despliega la carpeta INTEGRAIA20 en el n8n existente.
#
# Crea/actualiza en el n8n ya desplegado (contenedor `n8n-container`) una copia
# paralela de los 7 workflows de INTEGRAIA, adaptada a Odoo 20 (base
# `lead20.integraia.lat` y token `x-chatbot-token` en todos los nodos HTTP a Odoo),
# dentro de la carpeta INTEGRAIA20 (subcarpetas chatwoot/ycloud), SIN tocar los
# workflows 19.
#
# Idempotente: las copias llevan ids deterministas, así que re-ejecutar
# actualiza los mismos workflows _20 en lugar de duplicarlos.
#
# Requisitos: contenedores `n8n-container` y `odoo-db19-n8n` arriba; red
# `odoo_network_20` existente; `python3` en el host.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
N8N_CONTAINER="${N8N_CONTAINER:-n8n-container}"
N8N_DB_CONTAINER="${N8N_DB_CONTAINER:-odoo-db19-n8n}"
N8N_DB="${N8N_DB:-db_n8n}"
DB_USER="${DB_USER:-odoo}"
PROJECT_ID="${PROJECT_ID:-8nX7JPpIR54QE71D}"      # proyecto Personal
NET20="${NET20:-odoo_network_20}"
PG20_HOST="${PG20_HOST:-odoo-db20-leads}"
PG20_DB="${PG20_DB:-dbodoo20}"
PG20_USER="${PG20_USER:-odoo}"
PG20_PASSWORD_FILE="${PG20_PASSWORD_FILE:-$HERE/secrets/postgres_password.txt}"

psql_n8n() { docker exec -i "$N8N_DB_CONTAINER" psql -U "$DB_USER" -d "$N8N_DB" -tAc "$1"; }

echo "== 1) red n8n -> $NET20 =="
docker network connect "$NET20" "$N8N_CONTAINER" 2>/dev/null && echo "   conectada" || echo "   ya estaba conectada"

echo "== 2) credencial postgres-lead20 =="
if ! psql_n8n "SELECT 1 FROM credentials_entity WHERE name='postgres-lead20'" | grep -q 1; then
  PW="$(cat "$PG20_PASSWORD_FILE")"
  CID="$(python3 -c 'import secrets,string;print("".join(secrets.choice(string.ascii_letters+string.digits) for _ in range(16)))')"
  python3 - "$PW" "$CID" "$PG20_HOST" "$PG20_DB" "$PG20_USER" > /tmp/postgres-lead20.json <<'PY'
import json, sys
pw, cid, host, db, user = sys.argv[1:6]
print(json.dumps([{"id": cid, "name": "postgres-lead20", "type": "postgres",
    "data": {"host": host, "database": db, "user": user, "password": pw,
             "port": 5432, "ssl": "disable"}}], ensure_ascii=False))
PY
  chmod 600 /tmp/postgres-lead20.json
  docker cp /tmp/postgres-lead20.json "$N8N_CONTAINER:/tmp/postgres-lead20.json"
  docker exec "$N8N_CONTAINER" n8n import:credentials --input=/tmp/postgres-lead20.json >/dev/null
  docker exec "$N8N_CONTAINER" rm -f /tmp/postgres-lead20.json
  rm -f /tmp/postgres-lead20.json
  echo "   credencial creada"
else
  echo "   credencial ya existe"
fi
CRED_ID="$(psql_n8n "SELECT id FROM credentials_entity WHERE name='postgres-lead20'")"
echo "   credencial id=$CRED_ID"

echo "== 3) generar copias adaptadas =="
POSTGRES_CRED_ID="$CRED_ID" python3 "$HERE/n8n_json/build_integraia20.py"

echo "== 4) importar workflows (inactivos) =="
docker exec "$N8N_CONTAINER" rm -rf /tmp/int20 && docker exec "$N8N_CONTAINER" mkdir -p /tmp/int20
for d in chatwoot ycloud; do
  for f in "$HERE"/n8n_json/"$d"/*.json; do
    docker cp "$f" "$N8N_CONTAINER:/tmp/int20/$(basename "$f")" >/dev/null
  done
done
docker exec "$N8N_CONTAINER" n8n import:workflow --separate --input=/tmp/int20
docker exec "$N8N_CONTAINER" rm -rf /tmp/int20

echo "== 5) carpeta INTEGRAIA20 + asignacion =="
python3 - "$PROJECT_ID" > /tmp/folders20.sql <<'PY'
import hashlib, string, sys
A = string.ascii_letters + string.digits
def did(seed, n=17):
    h = hashlib.sha256(('integraia20-folder:' + seed).encode()).digest()
    x = int.from_bytes(h, 'big')
    return ''.join(A[(x >> (6 * i)) % 62] for i in range(n))
root, cw, yc = did('INTEGRAIA20'), did('INTEGRAIA20/chatwoot'), did('INTEGRAIA20/ycloud')
proj = sys.argv[1]
print("BEGIN;")
for fid, name, parent in ((root, 'INTEGRAIA20', 'NULL'), (cw, 'chatwoot', f"'{root}'"), (yc, 'ycloud', f"'{root}'")):
    print(f"INSERT INTO folder (id,name,\"parentFolderId\",\"projectId\",\"createdAt\",\"updatedAt\") "
          f"VALUES ('{fid}','{name}',{parent},'{proj}',now(),now()) ON CONFLICT (id) DO NOTHING;")
print(f"UPDATE workflow_entity SET \"parentFolderId\"='{cw}' WHERE name IN "
      "('chatbot_create_lead_0_con_menu_whatsapp_20','chatbot-simple_1_subflow_20','chatwoot_Sistema RAG standar Lead_20');")
print(f"UPDATE workflow_entity SET \"parentFolderId\"='{yc}' WHERE name IN "
      "('ycloud_create_lead_0_con_menu_whatsapp_20','yclod-simple_1_subflow_20','ycloud_carrito_subflow_20','Sistema RAG standar Leads_20');")
print("COMMIT;")
PY
docker exec -i "$N8N_DB_CONTAINER" psql -U "$DB_USER" -d "$N8N_DB" -v ON_ERROR_STOP=1 < /tmp/folders20.sql >/dev/null
rm -f /tmp/folders20.sql

echo "== listo: 7 workflows _20 en INTEGRAIA20 (inactivos) =="
psql_n8n "SELECT f.name, w.name FROM workflow_entity w LEFT JOIN folder f ON f.id=w.\"parentFolderId\" WHERE w.name LIKE '%_20' ORDER BY f.name, w.name;"
