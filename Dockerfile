FROM python:3.12-slim-bookworm

LABEL maintainer="Automation Labs / SkilLab <dev@automation-labs.co>"

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libxml2-dev \
    libxslt1-dev \
    libldap2-dev \
    libsasl2-dev \
    libssl-dev \
    libjpeg-dev \
    libfreetype6-dev \
    zlib1g-dev \
    node-less \
    npm \
    wkhtmltopdf \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Install rtlcss for RTL support
RUN npm install -g rtlcss

# Create odoo user
RUN useradd -m -d /opt/odoo -s /bin/bash odoo

# Copy source code
COPY --chown=odoo:odoo . /opt/odoo/src

# Install Python requirements
RUN pip install --no-cache-dir -r /opt/odoo/src/requirements.txt

# Create necessary directories
RUN mkdir -p /var/lib/odoo /mnt/extra-addons /etc/odoo \
    && chown -R odoo:odoo /var/lib/odoo /mnt/extra-addons /etc/odoo

# Copy config
COPY --chown=odoo:odoo odoo.conf /etc/odoo/odoo.conf

# Switch to odoo user
USER odoo

WORKDIR /opt/odoo/src

EXPOSE 8069

ENTRYPOINT ["python", "odoo-bin"]
CMD ["-c", "/etc/odoo/odoo.conf"]
