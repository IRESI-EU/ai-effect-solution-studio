FROM ai-effect-staging-web:0458b93949a4 AS installed
FROM node@sha256:4e6b70dd6cbfc88c8157ba19aa3d9f9cce6ba4703576d55459e45efcbc9c5f5d AS builder
WORKDIR /app
COPY --from=installed /app/node_modules ./node_modules
COPY --from=installed /app/apps/web/node_modules ./apps/web/node_modules
COPY --from=installed /app/pnpm-lock.yaml /baseline/pnpm-lock.yaml
COPY --from=installed /app/apps/web/package.json /baseline/web-package.json
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web ./apps/web
COPY examples ./examples
RUN cmp /baseline/pnpm-lock.yaml pnpm-lock.yaml && cmp /baseline/web-package.json apps/web/package.json
ENV NEXT_TELEMETRY_DISABLED=1 INTERNAL_API_URL=http://api:8080 NEXT_PUBLIC_ENVIRONMENT_LABEL="Restricted beta candidate · not deployed"
WORKDIR /app/apps/web
RUN --network=none node --test --test-isolation=none app/design-ai/page.test.cjs components/discovery-recommendation.test.cjs app/design-ai/workspace-view.test.ts
RUN --network=none node node_modules/next/dist/bin/next build --webpack

FROM node@sha256:4e6b70dd6cbfc88c8157ba19aa3d9f9cce6ba4703576d55459e45efcbc9c5f5d
ARG PORTAL_SOURCE_COMMIT
LABEL org.opencontainers.image.revision=$PORTAL_SOURCE_COMMIT
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 INTERNAL_API_URL=http://api:8080
WORKDIR /app
COPY --chown=node:node --from=builder /app/package.json /app/pnpm-lock.yaml /app/pnpm-workspace.yaml ./
COPY --chown=node:node --from=builder /app/node_modules ./node_modules
COPY --chown=node:node --from=builder /app/apps/web ./apps/web
USER node
WORKDIR /app/apps/web
EXPOSE 3000
CMD ["node", "node_modules/next/dist/bin/next", "start"]
