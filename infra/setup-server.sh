#!/usr/bin/env bash
# Prepare a fresh Ubuntu server (Oracle Always Free, ARM) for the app (PLAN.md section 12).
# Idempotent: safe to run again. Run as root: sudo bash setup-server.sh <deploy-user>
#
# What it does: security updates on, SSH by key only, firewall for 22/80/443, Docker, a deploy
# user that may run Docker, /opt/quote-engine for the compose files, a root-only env file
# template in /etc/quote-engine, and the nightly backup timer.
# Ports 80 and 443 must ALSO be opened in the OCI security list (the cloud firewall).
set -euo pipefail

DEPLOY_USER="${1:?usage: setup-server.sh <deploy-user>}"
APP_DIR=/opt/quote-engine
ETC_DIR=/etc/quote-engine

if [[ $EUID -ne 0 ]]; then
    echo "run as root" >&2
    exit 1
fi

echo "== packages and automatic security updates"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install --yes \
    ca-certificates curl gnupg unattended-upgrades iptables-persistent age rclone
dpkg-reconfigure --frontend=noninteractive unattended-upgrades

echo "== SSH: keys only"
install -d -m 0755 /etc/ssh/sshd_config.d
cat > /etc/ssh/sshd_config.d/10-quote-engine.conf <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
EOF
systemctl reload ssh

echo "== firewall: SSH, HTTP, HTTPS (Oracle images use iptables rules)"
for port in 22 80 443; do
    iptables -C INPUT -p tcp --dport "$port" -j ACCEPT 2>/dev/null \
        || iptables -I INPUT 1 -p tcp --dport "$port" -j ACCEPT
done
iptables -C INPUT -p udp --dport 443 -j ACCEPT 2>/dev/null \
    || iptables -I INPUT 1 -p udp --dport 443 -j ACCEPT
netfilter-persistent save

echo "== Docker"
if ! command -v docker >/dev/null; then
    install -d -m 0755 /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
    . /etc/os-release
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
        > /etc/apt/sources.list.d/docker.list
    apt-get update
    apt-get install --yes docker-ce docker-ce-cli containerd.io docker-compose-plugin
fi
systemctl enable --now docker

echo "== deploy user and folders"
id "$DEPLOY_USER" >/dev/null 2>&1 || useradd --create-home --shell /bin/bash "$DEPLOY_USER"
usermod -aG docker "$DEPLOY_USER"
install -d -m 0755 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "$APP_DIR"
install -d -m 0700 -o root -g root "$ETC_DIR"
if [[ ! -f "$ETC_DIR/app.env" ]]; then
    cat > "$ETC_DIR/app.env" <<'EOF'
# Root-only secrets for the app. Fill in every value; never commit this file.
DOMAIN=
POSTGRES_PASSWORD=
# age public key that backups are encrypted to (the private key stays in a password manager)
BACKUP_AGE_RECIPIENT=
# rclone remote names, configured with `rclone config` as root
BACKUP_REMOTE_NIGHTLY=
BACKUP_REMOTE_WEEKLY=
EOF
fi
# Readable by root and the deploy user's group only: docker compose needs it during deploys.
chgrp "$DEPLOY_USER" "$ETC_DIR" "$ETC_DIR/app.env"
chmod 0750 "$ETC_DIR"
chmod 0640 "$ETC_DIR/app.env"

echo "== nightly backup timer"
install -m 0755 "$(dirname "$0")/backup.sh" /usr/local/bin/quote-engine-backup
install -m 0644 "$(dirname "$0")/systemd/quote-engine-backup.service" /etc/systemd/system/
install -m 0644 "$(dirname "$0")/systemd/quote-engine-backup.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now quote-engine-backup.timer

echo "== done. Next: fill in $ETC_DIR/app.env, configure rclone as root, open 80/443 in OCI."
