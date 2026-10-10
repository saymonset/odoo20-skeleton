# ============================
# Dockerfile Odoo 20 CE lead — espejo del recipe 19 (SPEC 73)
# ============================

FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PATH="/opt/venv/bin:$PATH"
ENV ODOO_RC=/etc/odoo/odoo.conf
ENV PYDEVD_DISABLE_FILE_VALIDATION=1

# Dependencias del sistema (mismas que 19)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2-dev libxslt1-dev zlib1g-dev \
    libsasl2-dev libldap2-dev build-essential \
    libffi-dev default-libmysqlclient-dev \
    libpq-dev libjpeg62-turbo-dev liblcms2-dev \
    libblas-dev liblapack-dev git curl fontconfig \
    libxrender1 libxext6 xfonts-75dpi xfonts-base \
    libfreetype6 libfontconfig1 libjpeg62-turbo \
    postgresql-client xz-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# libssl1.1 (requisito del paquete wkhtmltopdf del recipe 19)
RUN curl -L --fail --silent --show-error \
      -o /tmp/libssl1.1.deb \
      http://archive.debian.org/debian/pool/main/o/openssl/libssl1.1_1.1.1w-0+deb11u1_amd64.deb \
    && dpkg -i /tmp/libssl1.1.deb || apt-get install -fy \
    && rm /tmp/libssl1.1.deb

# wkhtmltopdf (receta 19; PDFs no son objetivo de esta spec)
RUN curl -L --fail --silent --show-error \
      -o /tmp/wkhtml.deb \
      https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox_0.12.6-1.buster_amd64.deb \
    && dpkg -x /tmp/wkhtml.deb /tmp/wk \
    && mv /tmp/wk/usr/local/bin/wkhtmltopdf /usr/local/bin/ \
    && mv /tmp/wk/usr/local/bin/wkhtmltoimage /usr/local/bin/ \
    && chmod +x /usr/local/bin/wkhtmltopdf /usr/local/bin/wkhtmltoimage \
    && rm -rf /tmp/wkhtml.deb /tmp/wk

# Usuario Odoo
RUN groupadd -g 1001 odoo && \
    useradd -u 1001 -g odoo -m -d /opt/odoo odoo

# Entorno virtual
RUN python3 -m venv /opt/venv \
    && pip install --upgrade pip \
    && pip install debugpy

# Clonar Odoo 20 (rama estable 20.0, shallow)
RUN mkdir -p /opt/odoo/odoo-core && \
    git clone --depth 1 -b 20.0 https://github.com/odoo/odoo.git /opt/odoo/odoo-core && \
    chown -R odoo:odoo /opt/odoo/odoo-core

WORKDIR /opt/odoo

# Requirements: los del propio core 20.0 (no se copia el pinneado de 19) + dep de desarrollo
RUN pip install -r /opt/odoo/odoo-core/requirements.txt \
    && pip install pydevd-odoo

# Entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER 1001

ENTRYPOINT ["/entrypoint.sh"]
CMD []
