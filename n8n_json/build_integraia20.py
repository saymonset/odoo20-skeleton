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
import hashlib
import json
import os
import string
import sys
import uuid

SRC = sys.argv[1] if len(sys.argv) > 1 else '/home/odoo/lead/odoo19-skeleton/n8n_json'
OUT = os.path.dirname(os.path.abspath(__file__))

ALPHABET = string.ascii_letters + string.digits


def _det_id(name):
    """Id de workflow determinista (16 chars base62) para las copias INTEGRAIA20.

    Determinista => idempotente: re-ejecutar build + import actualiza el mismo
    workflow _20 en lugar de crear duplicados. Distinto del id 19 (prefijo de
    namespace) para no sobrescribir los workflows originales.
    """
    digest = hashlib.sha256(('integraia20:' + name).encode()).digest()
    num = int.from_bytes(digest, 'big')
    return ''.join(ALPHABET[(num >> (6 * i)) % 62] for i in range(16))


def _det_version_id(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, 'integraia20:' + name))

TOKEN_HEADER = "={{ $env.CHATBOT_API_TOKEN || '' }}"
URL_REPLACEMENTS = [
    ("$env.ODOO_APP_URL_YCLOUD || 'https://lead.integraia.lat'",
     "$env.ODOO_APP_URL_20 || 'https://lead20.integraia.lat'"),
    ("$env.ODOO_APP_URL || 'https://integraia.lat'",
     "$env.ODOO_APP_URL_20 || 'https://lead20.integraia.lat'"),
]
WEBHOOK_RENAME = {
    'chatwoot_integraia': 'chatwoot-integraia-20',
    'ycloud': 'ycloud-20',
}
# env var de subflow -> nombre del workflow destino (para calcular su id determinista)
SUBFLOW_TARGETS = {
    'N8N_SUBFLOW_CHATBOT_SIMPLE_ID_20': 'chatbot-simple_1_subflow_20',
    'N8N_SUBFLOW_YCLOUD_SIMPLE_ID_20': 'yclod-simple_1_subflow_20',
    'N8N_SUBFLOW_YCLOUD_CARRITO_ID_20': 'ycloud_carrito_subflow_20',
}
# credencial Postgres destino (dbodoo20); se pasa por entorno
POSTGRES_CRED_ID = os.environ.get('POSTGRES_CRED_ID', '')


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
    creds = node.get('credentials')
    if POSTGRES_CRED_ID and isinstance(creds, dict) and 'postgres' in creds:
        creds['postgres'] = dict(creds['postgres'], id=POSTGRES_CRED_ID)
    if node_type == 'n8n-nodes-base.httpRequest':
        _adapt_http(node)
    elif node_type == 'n8n-nodes-base.webhook':
        params = node.setdefault('parameters', {})
        if params.get('path') in WEBHOOK_RENAME:
            params['path'] = WEBHOOK_RENAME[params['path']]
    elif 'executeWorkflow' in node_type:
        wf = node.get('parameters', {}).get('workflowId')
        if isinstance(wf, dict):
            current = wf.get('value') or ''
            for env_name, target in SUBFLOW_TARGETS.items():
                base_env = env_name[:-3]  # sin el sufijo _20
                if base_env in current:
                    target_id = _det_id(target)
                    wf['value'] = "={{ $env.%s || '%s' }}" % (env_name, target_id)
                    wf['cachedResultUrl'] = '/workflow/%s' % target_id
                    wf['cachedResultName'] = target


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
            # ids propios y deterministas: nunca colisionan con los workflows 19
            data['id'] = _det_id(data['name'])
            data['versionId'] = _det_version_id(data['name'])
            data.pop('activeVersionId', None)
            data.pop('versionCounter', None)
            for node in data.get('nodes', []):
                _adapt_node(node)
            out_path = os.path.join(OUT, sub, filename)
            with open(out_path, 'w', encoding='utf-8') as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
            print('wrote', out_path)


if __name__ == '__main__':
    main()
