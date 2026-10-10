#!/usr/bin/env python3
"""Genera las copias INTEGRAIA20 de los workflows n8n, adaptadas a Odoo 20.

Transformaciones:
  - workflow `active` = False (importación inactiva; no toca el tráfico 19)
  - nombre del workflow con sufijo `_20`
  - URLs de Odoo -> $env.ODOO_APP_URL_20 || 'https://lead20.integraia.lat'
  - header `x-chatbot-token` en TODOS los nodos HTTP que llaman a Odoo
    (/ai_chatbot_1_portal/* y /chatbot_cart/*)
  - `/chatbot_cart/procesar` -> `/ai_chatbot_1_portal/procesar_paso`
  - webhooks renombrados (chatwoot-integraia-20 / ycloud-20)
  - subflows-call: env var renombrada a *_20 (el id real se parchea tras importar)

Uso:  python3 build_integraia20.py [SRC_DIR]
SRC_DIR por defecto: /home/odoo/lead/odoo19-skeleton/n8n_json
Salida: ./chatwoot/*.json y ./ycloud/*.json (junto a este script)
"""
import json
import os
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else '/home/odoo/lead/odoo19-skeleton/n8n_json'
OUT = os.path.dirname(os.path.abspath(__file__))

TOKEN_HEADER = "={{ $env.CHATBOT_API_TOKEN || '' }}"
URL_REPLACEMENTS = [
    ("$env.ODOO_APP_URL_YCLOUD || 'https://lead.integraia.lat'",
     "$env.ODOO_APP_URL_20 || 'https://lead20.integraia.lat'"),
    ("$env.ODOO_APP_URL || 'https://integraia.lat'",
     "$env.ODOO_APP_URL_20 || 'https://lead20.integraia.lat'"),
]
SUBFLOW_ENV_RENAME = [
    ('$env.N8N_SUBFLOW_CHATBOT_SIMPLE_ID', '$env.N8N_SUBFLOW_CHATBOT_SIMPLE_ID_20'),
    ('$env.N8N_SUBFLOW_YCLOUD_SIMPLE_ID', '$env.N8N_SUBFLOW_YCLOUD_SIMPLE_ID_20'),
    ('$env.N8N_SUBFLOW_YCLOUD_CARRITO_ID', '$env.N8N_SUBFLOW_YCLOUD_CARRITO_ID_20'),
]
WEBHOOK_RENAME = {
    'chatwoot_integraia': 'chatwoot-integraia-20',
    'ycloud': 'ycloud-20',
}


def _adapt_http(node):
    params = node.setdefault('parameters', {})
    url = params.get('url', '') or ''
    is_odoo = '/ai_chatbot_1_portal/' in url or '/chatbot_cart/' in url
    for old, new in URL_REPLACEMENTS:
        url = url.replace(old, new)
    if '/chatbot_cart/procesar' in url:
        url = url.replace('/chatbot_cart/procesar', '/ai_chatbot_1_portal/procesar_paso')
    params['url'] = url
    if not is_odoo:
        return
    headers = params.setdefault('headerParameters', {}).setdefault('parameters', [])
    if not any(h.get('name') == 'x-chatbot-token' for h in headers):
        headers.append({'name': 'x-chatbot-token', 'value': TOKEN_HEADER})
    params['sendHeaders'] = True


def _adapt_node(node):
    node_type = node.get('type') or ''
    if node_type == 'n8n-nodes-base.httpRequest':
        _adapt_http(node)
    elif node_type == 'n8n-nodes-base.webhook':
        params = node.setdefault('parameters', {})
        if params.get('path') in WEBHOOK_RENAME:
            params['path'] = WEBHOOK_RENAME[params['path']]
    elif 'executeWorkflow' in node_type:
        wf = node.get('parameters', {}).get('workflowId')
        if isinstance(wf, dict) and isinstance(wf.get('value'), str):
            for old, new in SUBFLOW_ENV_RENAME:
                wf['value'] = wf['value'].replace(old, new)


def main():
    for sub in ('chatwoot', 'ycloud'):
        src_dir = os.path.join(SRC, sub)
        if not os.path.isdir(src_dir):
            continue
        os.makedirs(os.path.join(OUT, sub), exist_ok=True)
        for filename in sorted(os.listdir(src_dir)):
            if not filename.endswith('.json'):
                continue
            with open(os.path.join(src_dir, filename), encoding='utf-8') as fh:
                data = json.load(fh)
            data['active'] = False
            if not (data.get('name') or '').endswith('_20'):
                data['name'] = (data.get('name') or '') + '_20'
            for node in data.get('nodes', []):
                _adapt_node(node)
            out_path = os.path.join(OUT, sub, filename)
            with open(out_path, 'w', encoding='utf-8') as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
            print('wrote', out_path)


if __name__ == '__main__':
    main()
