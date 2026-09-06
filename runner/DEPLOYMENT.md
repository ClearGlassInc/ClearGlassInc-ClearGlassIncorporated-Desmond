# Self-Hosted Runner — Deployment Guide

Live site for free: your VM runs nginx; GitHub Actions auto-deploys on every push to `main`.

---

## 1. Provision a VM

| Provider | Free tier | Notes |
|----------|-----------|-------|
| Oracle Cloud | Always-free 4 vCPU / 24 GB RAM | Best free option |
| AWS EC2 | t2.micro (1 yr free) | 1 vCPU / 1 GB |
| GCP e2-micro | Always-free | 0.25 vCPU / 1 GB |
| Azure B1s | 12 months free | 1 vCPU / 1 GB |

**OS**: Ubuntu 22.04 LTS  
**Inbound rules needed**: port 22 (SSH), 80 (HTTP), 443 (HTTPS optional)  
**Outbound**: 443 only (runner calls GitHub — no inbound needed for runner itself)

---

## 2. Get a runner registration token

1. Go to `https://github.com/ClearGlassInc/ClearGlassInc.github.io`
2. Settings → Actions → Runners → **New self-hosted runner**
3. Copy the token (valid 60 min)

---

## 3. Run the setup script

```bash
# On the VM (as root or with sudo)
git clone https://github.com/ClearGlassInc/ClearGlassInc.github.io.git /tmp/repo
cd /tmp/repo

RUNNER_TOKEN="<paste-token-here>" \
RUNNER_NAME="clearglass-runner-1" \
DOMAIN="yourdomain.com" \       # optional — omit if using IP only
sudo bash runner/setup-runner.sh
```

The script:
- Installs Node.js 20, Python 3, Docker, nginx, nmap, fail2ban
- Creates a non-root `github-runner` user
- Downloads & registers the GitHub Actions runner
- Registers it as a systemd service (starts on boot)
- Configures nginx to serve `/var/www/clearglass` on port 80

---

## 4. Allow the runner to reload nginx (sudoers)

```bash
echo "github-runner ALL=(ALL) NOPASSWD: /usr/bin/rsync, /bin/chown, /bin/chmod, /usr/sbin/nginx, /bin/systemctl reload nginx, /bin/mkdir" \
  | sudo tee /etc/sudoers.d/github-runner
sudo chmod 440 /etc/sudoers.d/github-runner
```

---

## 5. Push to main → site auto-deploys

```
git push origin main
```

The `self-hosted-deploy.yml` workflow runs on your VM, rsyncs the static site to
`/var/www/clearglass`, and reloads nginx. Your site is live at `http://<VM-IP>`.

---

## 6. Optional: free HTTPS with Let's Encrypt

If you have a domain pointing to the VM:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

Auto-renews via cron. HTTPS for free.

---

## 7. Useful commands

```bash
# Runner status
systemctl status actions.runner.*.service

# Runner logs
journalctl -u actions.runner.*.service -f

# nginx status
systemctl status nginx

# nginx logs
tail -f /var/log/nginx/access.log /var/log/nginx/error.log

# Re-register runner (new token)
sudo -u github-runner bash -c "cd /opt/actions-runner && ./config.sh remove --token <old-token>"
RUNNER_TOKEN=<new-token> sudo bash runner/setup-runner.sh
```

---

## Architecture

```
Push to main
     │
     ▼
GitHub Actions (triggered remotely)
     │
     ▼  (HTTPS outbound — runner polls GitHub)
Your VM (self-hosted runner process)
     │
     ├─ Checkout repo
     ├─ rsync _site/ → /var/www/clearglass/
     └─ systemctl reload nginx
                │
                ▼
        nginx serves site
        http://<VM-IP>:80
```
