# Deployment problems

Findings from reading `docker-compose.yml`, `infra/nginx/nginx.conf`, `backend/Dockerfile`,
`backend/.env.example`, `backend/app/main.py`, `README.md` §12 ("Getting started"), and the repo's
`.gitignore`/`.dockerignore` coverage. Each item is grounded in what's actually in the repo, not a
hypothetical — file:line points at the spot to fix. None of this touches application code; it's all
about whether the documented/composed deployment path actually runs.

**Headline finding:** the Docker Compose path — which `CLAUDE.md` calls "the intended one-command
path" — cannot currently start at all, and nothing in the repo's own documented steps ever exercises
it end-to-end, so the breakage was never caught. On this dev machine specifically, Docker isn't even
installed (per `CLAUDE.md`), so nobody has run `docker compose up` against this code, full stop.

## 1. `frontend` service has no Dockerfile — `docker compose up` fails immediately

`docker-compose.yml`'s `frontend:` service declares `build: context: ./frontend`, but there is no
`frontend/Dockerfile` in the repo (`backend/Dockerfile` exists; `frontend/Dockerfile` does not). The
very first `docker compose up` a judge or teammate runs stops here with a build error before any
other service even starts.

- **Fix:** add `frontend/Dockerfile`. For a dev-parity image matching the compose command
  (`npm run dev -- --host 0.0.0.0`), a simple `FROM node:20-alpine` + `COPY package*.json .` + `npm ci`
  + `COPY . .` + `EXPOSE 5173` is enough; for anything closer to production, build with `npm run build`
  and serve `dist/` from nginx instead (see #4, which would let nginx serve the built static files
  directly instead of proxying to a dev server).

## 2. No migration step in the Docker path — API starts against a schema-less database

`docker-compose.yml`'s `api`/`worker` services run `uvicorn app.main:app ...` / `celery -A ... worker`
directly — neither runs `alembic upgrade head` first, and there's no init container or entrypoint
script that does it either. Postgres comes up empty (fresh volume) and stays empty. Every DB-touching
endpoint (which is nearly all of them) fails until someone manually `docker exec`s into the `api`
container and runs the migration by hand. Contrast with README §12 step 4, which *does* run
`alembic upgrade head` — but that's the separate manual/native flow, not the compose services.

- **Fix:** run migrations as part of container startup — either an entrypoint script
  (`alembic upgrade head && exec "$@"`) on `api`, or a one-shot `migrate` service in
  `docker-compose.yml` that `api`/`worker` depend on with `condition: service_completed_successfully`.

## 3. nginx strips the `/api` prefix that every backend route requires

`infra/nginx/nginx.conf`:
```
location /api/ {
  proxy_pass http://api:8000/;
  ...
}
```
The trailing slash on `proxy_pass http://api:8000/` tells nginx to replace the matched `/api/` prefix
with `/` when forwarding — so a request to `http://localhost/api/v1/health` reaches the backend as
`/v1/health`. But every route is mounted at `/api/v1/...` (`backend/app/main.py:30-36`:
`app.include_router(health.router, prefix="/api/v1", ...)` and five more like it) — there is no route
at `/v1/health`. Anything sent through nginx's `/api/` location 404s.

- **Fix:** drop the trailing slash — `proxy_pass http://api:8000;` — so nginx forwards the full
  matched URI (`/api/v1/health`) unchanged instead of rewriting it.

## 4. Frontend bypasses nginx entirely, so #3 has never been exercised

`docker-compose.yml`'s `frontend` service sets `VITE_API_BASE_URL: http://localhost:8000` — the
browser calls the `api` container's own published port directly (`frontend/src/api/client.js:3-7`
builds `baseURL` from that env var), never going through nginx's `/api/` location at all. That's why
#3 shipped unnoticed: nginx's reverse-proxy path for the API is simply dead code in this compose file
today — port 80 only ever serves the frontend dev server, and every "single ingress on port 80" story
implied by having an nginx service is currently false.

- **Fix:** once #1 and #3 are fixed, point the frontend at the nginx-relative path (`VITE_API_BASE_URL`
  unset or `""`, with `client.js` defaulting to a relative `/api/v1`) so nginx on port 80 is the actual
  single entry point, matching what the compose file's shape implies.

## 5. The compose services nobody has run are exactly where the bugs are

README §12 "Getting started" documents a *hybrid* flow: `docker compose up -d postgres redis ollama`
for infrastructure only, then backend/worker/frontend are each run natively (`venv`, `pip install`,
`npm install`, etc.). The `api`, `worker`, `frontend`, and `nginx` services defined in
`docker-compose.yml` — where bugs #1, #2, #3 all live — are never invoked by any step README actually
documents. There is currently no single set of instructions in this repo that runs the full compose
stack end-to-end, which is exactly why a missing Dockerfile made it this far.

- **Fix:** either fix #1-#4 and rewrite README §12 to document `docker compose up` as the real
  one-command path (matching what `CLAUDE.md` already claims), or drop the unused `api`/`worker`/
  `frontend`/`nginx` compose services entirely and have `CLAUDE.md` stop describing them as intended —
  right now the docs and the compose file disagree about which path is real.

## 6. No `.dockerignore` in `backend/` — builds ship a 1.5GB local venv into the image context

`backend/.venv` is 1.5GB on disk on this machine, and there is no `backend/.dockerignore`. `COPY . .`
in `backend/Dockerfile:14` copies everything in the build context — including `.venv/`,
`__pycache__/`, `.pytest_cache/` — into the image, even though the image already installs its own
dependencies via `requirements.txt` two lines earlier. Every build sends a multi-gigabyte context to
the Docker daemon and bloats the resulting image for zero benefit.

- **Fix:** add `backend/.dockerignore` with at least `.venv/`, `__pycache__/`, `*.pyc`,
  `.pytest_cache/`, `.git/`. Add the same for `frontend/` (`node_modules/`, `dist/`) once #1 exists.

## 7. Ollama's model pull is a manual step with no readiness gate

The `ollama` service (`docker-compose.yml`) has no `healthcheck` — unlike `postgres` and `redis`,
which both do — and `api`/`worker`'s `depends_on` doesn't reference it at all. Nothing guarantees the
model named by `OLLAMA_MODEL` (`backend/.env.example`: `llama3.1:8b`) has actually been pulled before
the app starts accepting uploads. README documents a one-time manual
`docker exec -it ollama ollama pull llama3.1:8b`, but it's easy to skip or forget, and the first
extraction call after a fresh deploy just fails with no upfront signal that the step was missed.

- **Fix:** either bake the model into a custom `ollama` image (`FROM ollama/ollama` + `ollama pull` at
  build time) or add a one-shot init service that pulls the model and gates `api`/`worker` on its
  completion, the same shape suggested for migrations in #2.

## 8. nginx has no upload size limit set — defaults to 1MB, well under the app's 50MB limit

`backend/.env.example`: `MAX_UPLOAD_MB=50` is the backend's own ceiling for tender/bid PDFs, but
`infra/nginx/nginx.conf` sets no `client_max_body_size` anywhere, so nginx's built-in 1MB default
applies. Once #3/#4 are fixed and nginx becomes the real ingress, any PDF over ~1MB — which most real
tender documents will be — gets rejected by nginx with a 413 before the backend's 50MB limit is even
consulted.

- **Fix:** add `client_max_body_size 50m;` (matching `MAX_UPLOAD_MB`) inside nginx's `server {}` block.

## 9. No CI/CD and no deployment target beyond a developer's own machine

There's no `.github/workflows/`, no `fly.toml`/`render.yaml`/`Procfile`, nothing that runs tests on
push or defines where this actually gets deployed for a demo beyond `localhost`. That's a reasonable
scope for a hackathon prototype judged on a laptop — flagging it only so it isn't assumed there's a
hosted/shareable demo URL story anywhere in this repo right now.

---

## Suggested priority order

1. **#1 missing frontend Dockerfile** — nothing else in the compose path can even be tested until this
   exists.
2. **#2 migrations** and **#3 nginx prefix bug** — both make the compose stack silently non-functional
   even once it builds; fix together since they're both "first request after `docker compose up` just
   fails" bugs.
3. **#4 point the frontend at nginx** and **#8 upload size limit** — needed together, since fixing #4
   makes nginx the real ingress and #8 stops it rejecting real tender PDFs the moment it is.
4. **#7 Ollama readiness** — same "first request after deploy fails for a non-obvious reason" class as
   #2/#3, lower priority only because it's already partially documented as a manual step.
5. **#6 `.dockerignore`** and **#9 CI/CD** — hygiene and process gaps, not things that break a demo.
6. **#5 reconcile README vs. `CLAUDE.md`** — do this last, once the compose path in #1-#4 actually
   works, so the rewritten docs describe something true.
