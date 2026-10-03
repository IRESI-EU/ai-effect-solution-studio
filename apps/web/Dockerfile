FROM node:22-alpine AS dependencies

WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/package.json
RUN pnpm install --frozen-lockfile --filter @ai-effect/web...

FROM dependencies AS builder
COPY apps/web ./apps/web
RUN pnpm --filter @ai-effect/web build

FROM node:22-alpine AS runner

ENV NODE_ENV=production
WORKDIR /app
COPY --chown=node:node --from=builder /app/package.json /app/pnpm-lock.yaml /app/pnpm-workspace.yaml ./
COPY --chown=node:node --from=builder /app/node_modules ./node_modules
COPY --chown=node:node --from=builder /app/apps/web ./apps/web
USER node
WORKDIR /app/apps/web

EXPOSE 3000
CMD ["node", "node_modules/next/dist/bin/next", "start"]
