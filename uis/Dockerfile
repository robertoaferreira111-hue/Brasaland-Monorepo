# Single UI container for website (:3000) and backoffice (:3001).
# Apps are static HTML/CSS/JS (not Next.js); see Phase 0 discovery.
FROM node:22-alpine

WORKDIR /app

# 1) Container runtime: http-server (lockfile at /uis for reproducible install)
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

# 2) Website app deps from its own lockfile (Tailwind CLI tooling)
COPY website/package.json website/package-lock.json ./website/
RUN cd website && npm ci

# Backoffice has no package.json / lockfile — static assets only (verified Phase 0).

COPY website ./website
COPY backoffice ./backoffice
COPY start.sh ./start.sh

RUN chmod +x ./start.sh

EXPOSE 3000 3001

# Explicit sh so Node docker-entrypoint never treats start.sh as JS
CMD ["/bin/sh", "./start.sh"]
