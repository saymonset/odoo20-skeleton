# Odoo 20 CE lead (SPEC 73)

Stack mínimo para correr y ojear Odoo 20 CE en Docker, espejo del lead 19 pero
solo db+web (sin n8n/chatwoot/postiz/backups).

## Convención

| Elemento | Valor |
|----------|-------|
| Imagen | `odoo-pers:20` (rama `20.0` de odoo/odoo, python 3.12) |
| Web | `https://lead20.integraia.lat` (nginx del host; puertos `127.0.0.1:38069/38072`, sin exposición directa) |
| BD | `dbodoo20` con **demo** en `odoo-db20-leads` (host `:5436`, solo localhost) |
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
chmod a+rwX v20-leads/config v20-leads/logs v20-leads/odoo-web-data  # web corre como uid 1001 dentro del contenedor
bash 4_start-all.sh
```

## Uso diario

```bash
bash 4_start-all.sh              # up -d
bash 3_stop-all.sh               # down
bash 6_status_all_services.sh    # ps + stats
bash 7_logs_see_all_services.sh  # logs -f
```

Verificar versión: `curl -s https://lead20.integraia.lat/web/database/selector`

## nginx (acceso vía https://lead20.integraia.lat)

El vhost vive en `nginx-lead20.conf` (fuente versionada, espejo del bloque
`lead.integraia.lat` del 19 + `location /websocket` → gevent, necesario en 20.0).
Para re-aplicar en otro host:

```bash
sudo cp nginx-lead20.conf /etc/nginx/sites-available/odoo20.conf
sudo ln -sf /etc/nginx/sites-available/odoo20.conf /etc/nginx/sites-enabled/odoo20.conf
sudo certbot certonly --nginx -d lead20.integraia.lat --non-interactive --agree-tos
sudo nginx -t && sudo systemctl reload nginx
```

Prerequisitos: registro A `lead20.integraia.lat` → IP del host, y los snippets
`ssl.conf`/`letsencrypt.conf` de este servidor. Rollback: borrar symlink + reload.

**Revert del acceso directo:** si se necesita volver a exponer el puerto, quitar
el prefijo `127.0.0.1:` de los `ports` de `docker-compose.yaml` y `up -d
--force-recreate web-leads` (el nginx no lo necesita; solo se recomienda dejarlo
cerrado por seguridad).

## Notas

- `odoo.conf` lleva `without_demo = True` (opción booleana desde 19.0); el
  entrypoint lo anula en la inicialización con `--without-demo=False` para tener
  BD de ojeadura con demo.
- El bind de addons apunta a `modulos_odoo_20` (vacío a propósito; la migración
  de módulos 19→20 es spec futura).
- Este stack es lead: no se despliega nada de aquí a prod.
