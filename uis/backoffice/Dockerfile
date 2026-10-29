# Stage 6b will replace the current static backoffice with a Next.js App Router
# application. This image intentionally targets that final monorepo shape.
FROM node:22-alpine AS base

WORKDIR /app
RUN apk add --no-cache dumb-init

FROM base AS dependencies

COPY package.json package-lock.json ./
RUN npm ci

FROM dependencies AS development

COPY . .
EXPOSE 3001
ENTRYPOINT ["dumb-init", "--"]
CMD ["./node_modules/.bin/next", "dev", "-H", "0.0.0.0", "-p", "3001"]

FROM dependencies AS builder

ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
COPY . .
RUN npm run build

FROM base AS production

ENV NODE_ENV=production
COPY package.json package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/next.config.ts ./next.config.ts

EXPOSE 3001
ENTRYPOINT ["dumb-init", "--"]
CMD ["./node_modules/.bin/next", "start", "-H", "0.0.0.0", "-p", "3001"]
