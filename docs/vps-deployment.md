# VPS deployment procedure (Phase 4) — approval required before execution

This document is the **assessment + procedure**. It does **not** by itself mean production is deployed.

## Assessment findings (repository / local)

| Item | Status |
|------|--------|
| Authorized VPS hostname / IP | **Unknown — not in repo** |
| SSH user / key / jump host | **Unknown — agent will not guess credentials** |
| Current deploy directory on server | **Unknown** |
| Firewall / reverse proxy / domains | **Unknown** |
| Prebuilt vs build-on-server | **Default: build on VPS** with `docker compose … up --build` (Docker required) |
| Unrelated services on VPS | **Assume present** — do not prune/stop other containers |

Clone source for the server: `https://github.com/robertoaferreira111-hue/Brasaland-Monorepo.git`

## Architecture (production)

Same two-service architecture as local:

- `ui` — one container, website **:3000**, backoffice **:3001**
- `api` — FastAPI **:8000**, internal DNS name `api`
- Network: `brasaland-net`
- File: [`docker-compose.prod.yml`](../docker-compose.prod.yml) — **no bind mounts**, **no `--reload`**

Browser → API (same host): [`session.js`](../uis/backoffice/js/session.js) uses `http://<hostname>:8000` when not localhost.  
Container → API: `http://api:8000`.

## Secure env on the VPS

On the server only (never commit):

```bash
cp .env.example .env
chmod 600 .env
# Edit .env:
#   JWT_SECRET=<long-random-value-generated-on-server>
#   CORS_ORIGINS=http://YOUR_VPS_IP:3000,http://YOUR_VPS_IP:3001
```

## Proposed deploy commands (after your approval)

Replace `USER`, `VPS_HOST`, and paths with your real values.

```bash
# 1) From your laptop — connect (you supply the host/user/key)
ssh USER@VPS_HOST

# 2) On the VPS — inventory (non-destructive)
hostname -f
pwd
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}'
ss -tlnp | head -50   # or: sudo ss -tlnp

# 3) Clone or pull into a dedicated directory (do not overwrite unrelated apps)
mkdir -p ~/apps && cd ~/apps
git clone https://github.com/robertoaferreira111-hue/Brasaland-Monorepo.git
# or: cd Brasaland-Monorepo && git pull
cd Brasaland-Monorepo

# 4) Production env (on server only)
cp .env.example .env
chmod 600 .env
nano .env   # set JWT_SECRET + CORS_ORIGINS

# 5) Start production stack only (project name brasaland)
docker compose -f docker-compose.prod.yml up --build -d

# 6) Smoke tests (on VPS)
docker compose -f docker-compose.prod.yml ps
curl -sf http://127.0.0.1:8000/health
curl -sf -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3000/
curl -sf -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3001/
docker compose -f docker-compose.prod.yml exec -T ui wget -qO- http://api:8000/health

# 7) From your laptop / browser (after firewall allows 3000/3001/8000)
#    http://VPS_HOST:3000
#    http://VPS_HOST:3001
#    http://VPS_HOST:8000/health
```

**Firewall / ports:** open **3000**, **3001**, **8000** only with your explicit approval if not already open. Prefer documenting existing reverse-proxy routes if the school VPS already uses one.

## Rollback

```bash
cd ~/apps/Brasaland-Monorepo
docker compose -f docker-compose.prod.yml down
# Optional: remove only this project's images (do NOT docker system prune)
# docker compose -f docker-compose.prod.yml down --rmi local
```

Unrelated containers are untouched when using this project’s Compose file only (do not run global `docker stop $(docker ps -q)` or `docker system prune`).

## Restart policy

`restart: unless-stopped` on both services — containers come back after reboot when Docker starts.

## Evidence required for the assignment PR

1. SSH session on the VPS showing `hostname` and `docker compose -f docker-compose.prod.yml ps`
2. Public or LAN URLs for website, backoffice, and `/health`
3. Confirmation that other pre-existing containers still appear in `docker ps`

## Approval gate

Reply with:

1. VPS hostname or IP  
2. SSH user and how you authenticate (key path you will use — do not paste private keys)  
3. Preferred deploy directory  
4. Explicit approval: **“Approved to deploy to VPS”**  
5. Whether the agent may run SSH for you, or you will run the commands yourself  

Until then: **no production changes and no claim of successful VPS deployment.**
