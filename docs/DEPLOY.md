# Deploying AdaptAid

The tested target is **one small Linux server (VPS) running Docker Compose**, with Caddy in
front for automatic HTTPS. Everything (PostgreSQL, the API, the web app and the proxy) runs
from `docker-compose.yml`.

```
Internet ──443──▶ Caddy ──▶ web (Next.js, :3000) ──/api/*──▶ api (FastAPI, :8000) ──▶ db (PostgreSQL)
```

Only Caddy is exposed. The browser talks to one origin; the web container forwards `/api/*`
to the API, so the session cookie stays same-origin and httpOnly.

## 1. What you need

- A VPS with 2 GB RAM or more (1 vCPU is enough for a class), Ubuntu 22.04 or 24.04.
- A domain or subdomain whose DNS **A record** points at the server's IP address.
- Ports 80 and 443 open in the server's firewall.

## 2. Install Docker on the server

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # log out and back in afterwards
```

## 3. Get the code and configure it

```bash
git clone <your repository URL> adaptaid && cd adaptaid
cp .env.example .env
```

Edit `.env` and set at least:

| Variable | Value |
|---|---|
| `JWT_SECRET` | a long random string: `python3 -c "import secrets;print(secrets.token_urlsafe(48))"` |
| `POSTGRES_PASSWORD` | a strong password (used only inside Docker) |
| `COOKIE_SECURE` | `true` (the site is served over HTTPS) |
| `SITE_ADDRESS` | your domain, e.g. `adaptaid.example.com` |
| `TEACHER_INVITE_CODE` | the code teachers type when they register |
| `APP_ENV` | `prod` (disables the destructive `reset-db` / `reset-demo` commands) |

## 4. Start it

```bash
docker compose --profile prod up -d --build
docker compose --profile prod ps            # all services "healthy"
```

Caddy requests the HTTPS certificate on first start. Then load the course content and
create your administrator account:

```bash
docker compose exec api adaptaid seed
docker compose exec api adaptaid create-admin --email you@example.com --full-name "Your Name"
docker compose exec api adaptaid import-research      # offline results for the model report
docker compose exec api adaptaid apply-research       # research-validated recommender settings
```

Open `https://your-domain`, sign in as the administrator, and create teacher accounts (or
give teachers the invite code).

**For the pilot study:** do **not** run `seed-demo` on this server. Simulated students must
never mix with real pilot data. Use a laptop or a second instance for demos.

## 5. Updates

```bash
git pull
docker compose --profile prod up -d --build   # migrations run automatically on start
```

## 6. Backups

```bash
# nightly dump, kept for 14 days (crontab -e)
0 3 * * * cd ~/adaptaid && docker compose exec -T db pg_dump -U adaptaid adaptaid | gzip > ~/backups/adaptaid-$(date +\%F).sql.gz && find ~/backups -mtime +14 -delete
```

To restore: `gunzip -c backup.sql.gz | docker compose exec -T db psql -U adaptaid adaptaid`.

## 7. Test the production setup on your laptop

```bash
# in .env: SITE_ADDRESS=:80, COOKIE_SECURE=false
docker compose --profile prod up -d --build
docker compose exec api adaptaid seed
# open http://localhost
```

## 8. Background jobs

The API runs the nightly jobs (personas, risk, aid statistics, collaborative filtering, BKT
refit) at `JOB_HOUR` (Asia/Kolkata), and catches up on start if the last run is older than a
day. Run them any time from **Admin → Jobs**, or with `docker compose exec api adaptaid run-job all`.

## 9. Other hosts (untested)

The images also run on platforms such as Render, Railway or Fly.io: deploy `backend/Dockerfile`
with a managed PostgreSQL (`DATABASE_URL`), and `frontend/Dockerfile` (or Vercel) with
`BACKEND_URL` pointing at the API. Keep exactly one API process with `SCHEDULER_ENABLED=true`.
Free tiers that sleep or expire databases are not suitable for a pilot study.
