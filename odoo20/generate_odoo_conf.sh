#!/bin/bash
POSTGRES_PASS=$(cat secrets/postgres_password.txt)
sed "s/__POSTGRES_PASSWORD__/$POSTGRES_PASS/g" v20-leads/config/odoo.conf.dynamic > v20-leads/config/odoo.conf
echo "✅ Configuración generada en v20-leads/config/odoo.conf"
chmod 644 v20-leads/config/odoo.conf
