# Solution Studio production runbook

## How the four use cases run

The browser does not run the German, Portuguese, Danish, or Dutch models. The
browser talks to the Solution Studio web application, the web application talks
to its API, and that API submits a workflow to the shared WP3 orchestrator.
Workers in the orchestrator then call the country-node containers over a private
Docker network.

For the first production release, keep the portal, orchestrator, workers, and
all four country-node Docker stacks on the `evpa-uat` server. This is the least
complex arrangement and keeps model traffic off the public Internet. A country
node can move to another server later, but only if it exposes an authenticated,
TLS-protected endpoint that the orchestrator can reach.

```text
Public browser
    -> Traefik (HTTPS)
        -> Solution Studio web
            -> Solution Studio API
                -> WP3 orchestrator -> Redis -> workers
                    -> German containers
                    -> Portuguese containers
                    -> Danish containers
                    -> Dutch containers
```

Docker containers are processes, not permanent servers. `restart:
unless-stopped` makes them return after a server reboot. Docker volumes preserve
the portal database and workflow artifacts when containers are replaced.

## Release gates

Do not switch the public domains until all of these checks pass:

1. The portal database has a verified backup and a tested rollback procedure.
2. Redis, PostgreSQL, the orchestrator API, and country-node ports are not
   published to the Internet.
3. The portal web and API health checks pass in the private staging stack.
4. Each country workflow completes from the portal through the orchestrator,
   and its expected result artifact can be opened.
5. The management routes and all non-read-only API routes require credentials.
6. Both public domains return a valid TLS certificate after cutover.

## Private staging

Create `.env.production` from `.env.production.example`, generate a long random
PostgreSQL password, and keep the file mode at `600`. Then run:

```bash
docker compose \
  -f docker-compose.prod.yml \
  --env-file .env.production \
  build

docker compose \
  -f docker-compose.prod.yml \
  --env-file .env.production \
  up -d

curl --fail http://127.0.0.1:13000/
curl --fail http://127.0.0.1:13000/api/health
```

The staging port is bound to server loopback and is therefore available only on
the server or through an SSH tunnel. It does not replace the live portal.

## Country-node acceptance test

For every country, record the exact source revision and image digest, then:

1. Start its Compose stack on the shared `ai-effect-services` network.
2. Verify every service health endpoint from inside the Solution Studio API
   container.
3. Import or confirm its service manifests in the catalogue.
4. Create the representative country workflow.
5. Submit it through Solution Studio, not directly to the model.
6. Wait for a terminal `completed` state and open the output artifact.
7. Restart the country stack and repeat the health check to prove it survives a
   routine container replacement.

Passing a local model test alone is insufficient: the production test must
exercise portal -> API -> orchestrator -> worker -> country service -> artifact.

## Public cutover

Generate an `htpasswd` entry and store it in `STUDIO_BASIC_AUTH_USERS` in the
server-only environment file. The Traefik override keeps the public catalogue
read-only while protecting management pages and the API with Basic Auth.

During the agreed maintenance window:

1. Take a fresh database backup.
2. Stop only the old portal's Nginx container.
3. Start the new web service with both Compose files:

   ```bash
   docker compose \
     -f docker-compose.prod.yml \
     -f docker-compose.traefik.yml \
     --env-file .env.production \
     up -d
   ```

4. Check both domains, TLS, the public catalogue, protected management routes,
   and one non-destructive workflow.

## Rollback

If a cutover check fails, stop the new web router and restart the old Nginx
container. The old portal database and uploads are separate from the new
Solution Studio volumes, so this rollback does not require a database restore.
Keep the old stack and the pre-cutover backup until the new release has been
stable for an agreed observation period.
