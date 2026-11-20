---
name: railway-deploy
description: Prepare and check a Node/TypeScript repo (including npm-workspace monorepos with a web app, an API and shared packages) so it deploys to Railway as a single service. Covers railway.json, which packages must be runtime dependencies, Prisma, static file serving and env vars.
---

# Deploying a repo to Railway

Learned from `dashingstag/explore`, whose deploys failed until the fixes below were made (commits c6343d4, 2a05474, 9e9e6f9, 5b35889). Run the checklist against the target repo, change only what's missing, then do the local checks.

## 1. Use one service at the repo root (monorepos)
- If the apps import shared workspace packages (e.g. `packages/content`), **do not** give each app its own service with the service root directory set to `apps/web` or `apps/api`. Railway's build only sees that folder, so imports from outside it fail. Use one service built from the repo root, with the root directory left empty.
- Delete per-app `railway.toml` files and put a single `railway.json` at the root:
  ```json
  {
    "$schema": "https://railway.app/railway.schema.json",
    "build": { "builder": "NIXPACKS", "buildCommand": "npm run build" },
    "deploy": {
      "startCommand": "npm start",
      "healthcheckPath": "/health",
      "restartPolicyType": "ON_FAILURE",
      "restartPolicyMaxRetries": 5
    }
  }
  ```
- Root `package.json` needs:
  - `"build"`: build the web app first, then the API, e.g. `npm run build -w apps/web && npm run build -w apps/api`.
  - `"start"`: `npm run start -w apps/api`.
  - `"engines": { "node": ">=20" }`.
- Leave `package-lock.json` committed and in sync with `package.json`.

## 2. Have the API serve the built frontend (same origin)
- Railway serves one public domain per service, so the API also serves the web app's `dist/`. The frontend then calls the API on the same origin, with no CORS setup and no separate API URL. Example, Hono + `@hono/node-server`:
  ```ts
  const webDist = fileURLToPath(new URL('../../web/dist', import.meta.url));
  app.use('/*', serveStatic({ root: webDist }));
  const spaFallback = serveStatic({ path: join(webDist, 'index.html') });
  app.get('*', async (c, next) => {
    const { path } = c.req;
    if (path.startsWith('/api/') || /\.[a-z0-9]+$/i.test(path)) return c.notFound(); // real 404s
    return (await spaFallback(c, next)) ?? c.notFound();
  });
  ```
  Register these routes **after** all API routes. Only page routes should fall back to `index.html`. Missing assets and unknown `/api/*` paths must return 404; otherwise clients receive HTML where they expected JS or JSON.
- Frontend API base URL: `import.meta.env.VITE_API_URL ?? ''`. An empty string means same origin. `VITE_*` values are baked in at build time, so leave them unset on Railway.
- Listen on `Number(process.env.PORT ?? <dev port>)`. Railway sets `PORT`.
- Add `GET /health` that returns 200 and doesn't touch the database (it's the healthcheck path).

## 3. Put everything `npm start` uses in `dependencies`
Railway's build removes `devDependencies` before the app starts. Anything the **start command** runs must be in `dependencies` of the workspace that runs it. Typical examples: `tsx` (if the server runs TS directly), `prisma` (the CLI, for `migrate deploy`) and `@prisma/client`.
- After moving them, run `npm install` to regenerate the lockfile and commit it. A stale lockfile still marks them `"dev": true`, and they get removed anyway (this was the cause of explore's failure at commit 2a05474).
- Check: `npm ls --omit=dev -w <api-workspace> tsx prisma` must list both packages.

## 4. Prisma
- Build: `"build": "prisma generate && tsc --noEmit"` (or your compile step). Without `prisma generate`, the generated client types don't exist on Railway and the type check fails.
- Start: `"start": "prisma migrate deploy && tsx src/index.ts"`. Every migration must be committed under `prisma/migrations/`.
- **`prisma migrate deploy` exits with an error when `DATABASE_URL` is unset** (Prisma 5: "Environment variable not found"), so the service fails to boot. Either attach Postgres before the first deploy, or, if the app should run without a database, guard it: `([ -z "$DATABASE_URL" ] || prisma migrate deploy) && tsx src/index.ts`.
- Create the Prisma client lazily, and return 503 from routes that need the database when `DATABASE_URL` is missing. The rest of the app then keeps working without a database.

## 5. Railway project setup (user does this in the dashboard)
1. New project → Deploy from GitHub repo. Leave the root directory empty.
2. Settings → Networking → Generate Domain.
3. Optional database: add a PostgreSQL service, then in the app service's Variables set `DATABASE_URL=${{Postgres.DATABASE_URL}}`. Migrations run at start.
4. Set app secrets as service variables (for explore: `ADMIN_TOKEN`, `TEACHER_TOKEN`, `PARENT_TOKEN`). `WEB_ORIGIN` (CORS) is only needed if the frontend is hosted on a different origin. Keep `.env.example` listing every variable.

## 6. Check locally before pushing
```bash
npm install                                  # lockfile in sync, no unexpected diff
npm run build                                # same command Railway runs
npm ls --omit=dev -w <api-workspace> tsx prisma
PORT=8080 DATABASE_URL=<local pg or unset if guarded> npm start &
curl -fsS localhost:8080/health
curl -fsS localhost:8080/ | grep -q '<div id="root"'                # SPA served
curl -s -o /dev/null -w '%{http_code}\n' localhost:8080/api/nope    # expect 404
curl -s -o /dev/null -w '%{http_code}\n' localhost:8080/missing.js  # expect 404
```
A local Postgres for the check: `docker compose up -d` (explore ships a `postgres:16-alpine` compose file), then use its URL.

## 7. Document it
Add a "Deploying on Railway" section to the README: single service at the repo root, what `build`/`start` do, the health path, the database step, and a warning not to set a per-app root directory.
