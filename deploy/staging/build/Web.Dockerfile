FROM node@sha256:4e6b70dd6cbfc88c8157ba19aa3d9f9cce6ba4703576d55459e45efcbc9c5f5d AS dependencies
WORKDIR /app
COPY --from=locked_inputs /tools/pnpm-11.25.0.tgz /tmp/pnpm.tgz
COPY deploy/staging/build/inputs.lock.json /tmp/inputs.lock.json
RUN node -e "const fs=require('fs'),c=require('crypto'),l=require('/tmp/inputs.lock.json');if(c.createHash('sha256').update(fs.readFileSync('/tmp/pnpm.tgz')).digest('hex')!==l.tool_archive.sha256)process.exit(1)" \
    && mkdir /opt/pnpm && tar -xzf /tmp/pnpm.tgz -C /opt/pnpm --strip-components=1 \
    && chmod 0755 /opt/pnpm/bin/pnpm.cjs \
    && ln -s /opt/pnpm/bin/pnpm.cjs /usr/local/bin/pnpm && pnpm --version
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/package.json
RUN --network=default pnpm install --frozen-lockfile --filter @ai-effect/web...

FROM dependencies AS builder
ARG PORTAL_SOURCE_COMMIT
ENV NEXT_TELEMETRY_DISABLED=1 INTERNAL_API_URL=http://api:8080 NEXT_PUBLIC_ENVIRONMENT_LABEL="Disconnected local staging review"
COPY apps/web ./apps/web
COPY examples ./examples
WORKDIR /app/apps/web
RUN --network=none node --experimental-strip-types --test --test-isolation=none app/deployments/results.test.ts app/design-ai/allowance.test.ts app/design-ai/session.test.ts app/publish/guided-manifest.test.ts lib/*.test.ts
RUN --network=none node node_modules/next/dist/bin/next typegen
RUN --network=none node node_modules/typescript/bin/tsc --noEmit -p tsconfig.json
RUN --network=none node node_modules/next/dist/bin/next build --webpack

FROM node@sha256:4e6b70dd6cbfc88c8157ba19aa3d9f9cce6ba4703576d55459e45efcbc9c5f5d AS runtime
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
