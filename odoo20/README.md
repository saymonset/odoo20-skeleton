# Odoo 20 CE lead (SPEC 73)

Stack mínimo para correr y ojear Odoo 20 CE en Docker, espejo del lead 19 pero
solo db+web (sin n8n/chatwoot/postiz/backups).

## Convención

| Elemento | Valor |
|----------|-------|
| Imagen | `odoo-pers:20` (rama `20.0` de odoo/odoo, python 3.12) |
| Web | `http://localhost:38069` (gevent `:38072`) |
| BD | `dbodoo20` con **demo** en `odoo-db20-leads` (host `:5436`) |
| Manager (master) | `admin` / `admin` (mismo criterio que lead 19) |
| Red | `odoo_network_20` (externa) |
| Addons custom | bind de `/home/odoo/lead/modulos_odoo_20/shared/{extra,oca}/20.0` |

## Puesta a punto (primera vez)

```bash
cd /home/odoo/lead/odoo20-skeleton/odoo20

# 0) Red externa (solo una vez)
docker network create odoo_network_20

# 1) Secret de PostgreSQL (solo una vez; gitignored)
mkdir -p secrets && openssl rand -hex 16 > secrets/postgres_password.txt

# 2) Config renderizado desde la plantilla
bash generate_odoo_conf.sh

# 3) Imagen (~5-10 min; clona 20.0 y usa su requirements.txt)
bash 1_build_imagen.sh

# 4) Arranque; el entrypoint crea dbodoo20 y la inicializa con demo (~3-5 min)
mkdir -p v20-leads/{pgdata/data,pgdata/init,odoo-web-data,logs}
bash 4_start-all.sh
```

## Uso diario

```bash
bash 4_start-all.sh              # up -d
bash 3_stop-all.sh               # down
bash 6_status_all_services.sh    # ps + stats
bash 7_logs_see_all_services.sh  # logs -f
```

Verificar versión: `curl -s http://localhost:38069/web/database/selector`

## Notas

- `odoo.conf` lleva `without_demo = all`; el entrypoint lo anula en la
  inicialización con `--without-demo=False` para tener BD de ojeadura con demo.
- El bind de addons apunta a `modulos_odoo_20` (vacío a propósito; la migración
  de módulos 19→20 es spec futura).
- Este stack es lead: no se despliega nada de aquí a prod.
