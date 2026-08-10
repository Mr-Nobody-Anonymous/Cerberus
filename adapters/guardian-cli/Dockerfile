# Multi-stage Dockerfile for Guardian CLI with Alpine Linux
# Installs all 15 security tools for comprehensive penetration testing

# ============================================================================
# Tool Stages: Pull official binaries or build from source
# ============================================================================
# Build ffuf from source (official image not available/public)
FROM golang:alpine AS builder
RUN go install -v github.com/ffuf/ffuf/v2@latest

# Pull official binaries for other tools
FROM projectdiscovery/httpx:latest AS httpx
FROM projectdiscovery/subfinder:latest AS subfinder
FROM projectdiscovery/nuclei:latest AS nuclei
FROM ghcr.io/oj/gobuster:latest AS gobuster
FROM owaspamass/amass:latest AS amass
FROM zricethezav/gitleaks:latest AS gitleaks

# ============================================================================
# Stage 2: Runtime - Python environment with all tools
# ============================================================================
FROM python:3.11-alpine

LABEL maintainer="Guardian Security Team"
LABEL description="AI-Powered Penetration Testing Automation Platform"
LABEL version="1.0.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    GUARDIAN_HOME=/guardian

WORKDIR ${GUARDIAN_HOME}

# Install system dependencies and security tools
# Added gcompat for Go binary compatibility
RUN apk add --no-cache \
    # Build dependencies
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    # Network tools
    nmap \
    nmap-scripts \
    git \
    curl \
    gcompat \
    # Ruby for WhatWeb and WPScan
    ruby \
    ruby-dev \
    ruby-bundler \
    # Nikto dependencies
    perl \
    perl-net-ssleay \
    # Masscan build dependencies
    make \
    && \
    # Install Nikto
    git clone https://github.com/sullo/nikto /opt/nikto && \
    ln -s /opt/nikto/program/nikto.pl /usr/local/bin/nikto && \
    chmod +x /usr/local/bin/nikto && \
    # Install Masscan
    git clone https://github.com/robertdavidgraham/masscan /opt/masscan && \
    cd /opt/masscan && make && make install && \
    cd ${GUARDIAN_HOME} && \
    # Install WhatWeb
    git clone https://github.com/urbanadventurer/WhatWeb.git /opt/whatweb && \
    ln -s /opt/whatweb/whatweb /usr/local/bin/whatweb && \
    chmod +x /usr/local/bin/whatweb && \
    # Install WPScan
    gem install wpscan --no-document && \
    # Clean up build dependencies
    apk del make gcc musl-dev

# Copy Go tools from official images
COPY --from=httpx /usr/local/bin/httpx /usr/local/bin/
COPY --from=subfinder /usr/local/bin/subfinder /usr/local/bin/
COPY --from=nuclei /usr/local/bin/nuclei /usr/local/bin/
COPY --from=gobuster /app/gobuster /usr/local/bin/gobuster
COPY --from=builder /go/bin/ffuf /usr/local/bin/
COPY --from=amass /bin/amass /usr/local/bin/
COPY --from=gitleaks /usr/bin/gitleaks /usr/local/bin/

# Install Python-based security tools
RUN pip install --no-cache-dir \
    wafw00f \
    sqlmap \
    sslyze \
    arjun \
    dnsrecon

# Install CMSeeK
RUN git clone https://github.com/Tuhinshubhra/CMSeeK.git /opt/cmseek && \
    pip install -r /opt/cmseek/requirements.txt && \
    ln -s /opt/cmseek/cmseek.py /usr/local/bin/cmseek && \
    chmod +x /usr/local/bin/cmseek

# Download TestSSL
RUN git clone --depth 1 https://github.com/drwetter/testssl.sh.git /opt/testssl && \
    ln -s /opt/testssl/testssl.sh /usr/local/bin/testssl

# Install XSStrike
RUN git clone https://github.com/s0md3v/XSStrike.git /opt/xsstrike && \
    pip install -r /opt/xsstrike/requirements.txt && \
    ln -s /opt/xsstrike/xsstrike.py /usr/local/bin/xsstrike && \
    chmod +x /usr/local/bin/xsstrike

# Copy Guardian application files
COPY pyproject.toml ./
COPY README.md ./
COPY ai/ ./ai/
COPY cli/ ./cli/
COPY core/ ./core/
COPY tools/ ./tools/
COPY utils/ ./utils/
COPY workflows/ ./workflows/
COPY config/ ./config/
COPY reports/ ./reports/

# Install Guardian and its dependencies
RUN pip install --no-cache-dir -e .

# Create directories for reports and logs
RUN mkdir -p /guardian/reports /guardian/logs && \
    chmod 777 /guardian/reports /guardian/logs

# Create non-root user for security
RUN addgroup -g 1000 guardian && \
    adduser -D -u 1000 -G guardian guardian && \
    chown -R guardian:guardian ${GUARDIAN_HOME}

# Switch to non-root user
USER guardian

# Update Nuclei templates on container start
RUN nuclei -update-templates || true

# Set entry point
ENTRYPOINT ["python", "-m", "cli.main"]
CMD ["--help"]
