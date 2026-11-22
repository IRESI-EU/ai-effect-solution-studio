# Reuse only dependencies whose lock/package manifests match this source.
FROM ai-effect-beta-candidate-web:002686f04fb5@sha256:ced615705bfc07ad59fd6489491959d9b0a3ff18a54421ad9a6df6aa37d477f6 AS dependencies
FROM node@sha256:4e6b70dd6cbfc88c8157ba19aa3d9f9cce6ba4703576d55459e45efcbc9c5f5d AS builder
COPY --from=dependencies /app/node_modules /app/node_modules
COPY --from=dependencies /app/apps/web/node_modules /app/apps/web/node_modules
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web ./apps/web
COPY examples ./examples
RUN --network=none node -e "const f=require('fs'),c=require('crypto');for(const [p,h] of Object.entries({'pnpm-lock.yaml':'e24751ceba65437292f017cfb3b19ab55613a0f2731391ef56cf3808b6284cd6','package.json':'8a01d802a14ac1fed96e63609644f8b7ce5f7e763bdc4a34078844943d4735d1','apps/web/package.json':'1a5f4933e452260cc4e75fdd84c92a358d9010ffe56e41277b0261e506bdff1f'})){if(c.createHash('sha256').update(f.readFileSync(p,'utf8').replace(/\r\n/g,'\n')).digest('hex')!==h)throw Error('Dependency manifest changed: '+p)}"
ENV NEXT_TELEMETRY_DISABLED=1 INTERNAL_API_URL=http://api:8080 NEXT_PUBLIC_ENVIRONMENT_LABEL="R1 candidate - AI disabled / NOT RELEASED"
WORKDIR /app/apps/web
RUN --network=none node --experimental-strip-types --test --test-isolation=none app/deployments/results.test.ts app/design-ai/allowance.test.ts app/design-ai/session.test.ts app/publish/guided-manifest.test.ts lib/*.test.ts components/selected-input-results.test.cjs
RUN --network=none node node_modules/next/dist/bin/next typegen \
    && node node_modules/typescript/bin/tsc --noEmit -p tsconfig.json \
    && node node_modules/next/dist/bin/next build --webpack

FROM node@sha256:4e6b70dd6cbfc88c8157ba19aa3d9f9cce6ba4703576d55459e45efcbc9c5f5d
ARG PORTAL_SOURCE_COMMIT
LABEL org.opencontainers.image.revision=$PORTAL_SOURCE_COMMIT
LABEL org.opencontainers.image.source="https://github.com/IRESI-EU/ai-effect-solution-studio"
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 INTERNAL_API_URL=http://api:8080
WORKDIR /app
COPY --chown=node:node --from=builder /app/package.json /app/pnpm-lock.yaml /app/pnpm-workspace.yaml ./
COPY --chown=node:node --from=builder /app/node_modules ./node_modules
COPY --chown=node:node --from=builder /app/apps/web ./apps/web
USER node
WORKDIR /app/apps/web
EXPOSE 3000
CMD ["node", "node_modules/next/dist/bin/next", "start"]
