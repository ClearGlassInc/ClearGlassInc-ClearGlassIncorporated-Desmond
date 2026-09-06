#!/bin/bash
# ClearGlassInc Self-Hosted GitHub Actions Runner Setup
# OS: Ubuntu 22.04 LTS
# Runs as non-root user; exposes site via nginx on port 80/443
set -euo pipefail

###############################################################################
# CONFIG — edit these before running
###############################################################################
REPO_URL="${REPO_URL:-https://github.com/ClearGlassInc/ClearGlassInc.github.io}"
RUNNER_TOKEN="${RUNNER_TOKEN:-}"          # from Settings > Actions > Runners > New
RUNNER_NAME="${RUNNER_NAME:-clearglass-runner-1}"
RUNNER_USER="github-runner"
RUNNER_DIR="/opt/actions-runner"
RUNNER_VERSION="2.317.0"                 # update to latest as needed
SITE_DIR="/var/www/clearglass"
RELEASES_DIR="/var/www/clearglass-releases"
DOMAIN="${DOMAIN:-}"                     # optional: set to your domain for HTTPS
###############################################################################

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

[[ $EUID -ne 0 ]] && error "Run as root: sudo bash setup-runner.sh"
[[ -z "$RUNNER_TOKEN" ]] && error "Set RUNNER_TOKEN before running. Get it from:\n  GitHub repo > Settings > Actions > Runners > New self-hosted runner"

###############################################################################
# 1. System packages
###############################################################################
info "Updating packages and installing dependencies..."
apt-get update -qq
apt-get install -y --no-install-recommends \
    curl wget git unzip jq ca-certificates gnupg lsb-release \
    build-essential cmake pkg-config \
    python3 python3-pip python3-venv \
    libssl-dev libffi-dev \
    nginx \
    nmap netcat-openbsd \
    fail2ban ufw

###############################################################################
# 2. Node.js 20 LTS
###############################################################################
if ! command -v node &>/dev/null; then
    info "Installing Node.js 20 LTS..."
    # Download the NodeSource setup script to disk and execute it as a separate
    # step rather than piping curl straight into a shell — a fetched script that
    # can't be inspected before it runs is a supply-chain risk (defender:
    # curl_pipe_shell). Fetch, run, then remove.
    nodesource_setup="$(mktemp)"
    curl -fsSL https://deb.nodesource.com/setup_20.x -o "$nodesource_setup"
    bash "$nodesource_setup"
    rm -f "$nodesource_setup"
    apt-get install -y nodejs
fi

###############################################################################
# 3. Docker
###############################################################################
if ! command -v docker &>/dev/null; then
    info "Installing Docker..."
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
        https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
        > /etc/apt/sources.list.d/docker.list
    apt-get update -qq
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin
    systemctl enable --now docker
fi

###############################################################################
# 4. Non-root runner user
###############################################################################
if ! id "$RUNNER_USER" &>/dev/null; then
    info "Creating user: $RUNNER_USER"
    useradd -m -s /bin/bash "$RUNNER_USER"
fi
usermod -aG docker "$RUNNER_USER"

###############################################################################
# 5. Download & configure the runner
###############################################################################
info "Setting up runner in $RUNNER_DIR..."
mkdir -p "$RUNNER_DIR"
chown "$RUNNER_USER":"$RUNNER_USER" "$RUNNER_DIR"

ARCH="x64"
TARBALL="actions-runner-linux-${ARCH}-${RUNNER_VERSION}.tar.gz"
DOWNLOAD_URL="https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/${TARBALL}"

if [[ ! -f "$RUNNER_DIR/config.sh" ]]; then
    info "Downloading GitHub Actions runner v${RUNNER_VERSION}..."
    curl -fsSL -o "/tmp/${TARBALL}" "$DOWNLOAD_URL"
    tar xzf "/tmp/${TARBALL}" -C "$RUNNER_DIR"
    rm "/tmp/${TARBALL}"
    chown -R "$RUNNER_USER":"$RUNNER_USER" "$RUNNER_DIR"
fi

info "Configuring runner..."
sudo -u "$RUNNER_USER" bash -c "
    cd '$RUNNER_DIR'
    ./config.sh \
        --url '$REPO_URL' \
        --token '$RUNNER_TOKEN' \
        --name '$RUNNER_NAME' \
        --labels 'self-hosted,linux,x64,clearglass' \
        --work '_work' \
        --unattended \
        --replace
"

###############################################################################
# 6. systemd service (written by svc.sh, then hardened)
###############################################################################
info "Registering runner as systemd service..."
cd "$RUNNER_DIR"
sudo -u "$RUNNER_USER" bash -c "cd '$RUNNER_DIR' && ./svc.sh install $RUNNER_USER"

# Harden the unit file
SERVICE_FILE="/etc/systemd/system/actions.runner.$(echo "$REPO_URL" | sed 's|https://github.com/||;s|/|.|g').${RUNNER_NAME}.service"
if [[ -f "$SERVICE_FILE" ]]; then
    # Append security directives if not already present
    if ! grep -q "NoNewPrivileges" "$SERVICE_FILE"; then
        sed -i '/\[Service\]/a NoNewPrivileges=yes\nPrivateTmp=yes\nProtectSystem=full\nProtectHome=yes\nReadWritePaths='"$RUNNER_DIR"' /tmp' "$SERVICE_FILE"
    fi
fi

systemctl daemon-reload
sudo -u "$RUNNER_USER" bash -c "cd '$RUNNER_DIR' && ./svc.sh start"
systemctl enable "$(systemctl list-units --type=service | grep actions.runner | awk '{print $1}')" 2>/dev/null || true

###############################################################################
# 7. nginx — serve the static site
###############################################################################
info "Configuring nginx to serve the site..."
mkdir -p "$SITE_DIR" "$RELEASES_DIR" "$SITE_DIR/current"
chown -R www-data:www-data "$SITE_DIR" "$RELEASES_DIR"
usermod -aG www-data "$RUNNER_USER"   # runner can write to site dir

cat > /etc/nginx/sites-available/clearglass <<NGINX
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN:-_};

    root $SITE_DIR/current;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;

    # Cache static assets
    location ~* \.(css|js|png|jpg|gif|ico|svg|woff2?)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Block dot files
    location ~ /\. { deny all; }

    gzip on;
    gzip_types text/plain text/css application/javascript application/json image/svg+xml;
}
NGINX

ln -sf /etc/nginx/sites-available/clearglass /etc/nginx/sites-enabled/clearglass
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable --now nginx

###############################################################################
# 8. Optional HTTPS via Certbot
###############################################################################
if [[ -n "$DOMAIN" ]]; then
    info "Setting up Let's Encrypt for $DOMAIN..."
    apt-get install -y certbot python3-certbot-nginx
    certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "admin@${DOMAIN}" \
        --redirect || warn "Certbot failed — run manually: certbot --nginx -d $DOMAIN"
fi

###############################################################################
# 9. Firewall: outbound 443 only for runner; inbound 80/443 for site
###############################################################################
info "Configuring UFW firewall..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw deny 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

###############################################################################
# 10. fail2ban service bootstrap (no SSH exposure assumed)
###############################################################################
systemctl enable --now fail2ban

###############################################################################
# Done
###############################################################################
info "Setup complete!"
echo ""
echo "  Runner name : $RUNNER_NAME"
echo "  Runner dir  : $RUNNER_DIR"
echo "  Site dir    : $SITE_DIR"
echo "  Site URL    : http://${DOMAIN:-<YOUR_VM_IP>}"
echo ""
echo "Next: push to main — the workflow will auto-deploy your site."
echo "Check runner status: systemctl status actions.runner.*.service"
