from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from app.models import init_db, SessionLocal, User, Movie, Snack, Rental
from app.seed import seed
from app.auth import create_token, get_current_user


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed()
    yield


app = FastAPI(title="Starlite Video BBS API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "starlite-bbs-api"}


class LoginReq(BaseModel):
    username: str
    password: str


@app.post("/api/v1/login")
def login(req: LoginReq, db=Depends(db_session)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or user.password != req.password:
        raise HTTPException(status_code=401, detail="bad credentials")
    token = create_token(user.id, user.username, user.is_admin)
    return {"access_token": token, "token_type": "bearer", "user_id": user.id}


# ---------------- Movies ----------------

@app.get("/api/v1/movies")
def list_movies(limit: int = 50, db=Depends(db_session)):
    # VULN 3: BOPLA - excessive data exposure / no upper bound on limit,
    # lets an attacker dump the entire table via ?limit=9999
    q = db.query(Movie).limit(limit).all()
    return [
        {"id": m.id, "title": m.title, "genre": m.genre, "year": m.year,
         "rental_price": m.rental_price, "stock": m.stock}
        for m in q
    ]


@app.get("/api/v1/movies/{movie_id}")
def get_movie(movie_id: int, db=Depends(db_session)):
    m = db.get(Movie, movie_id)
    if not m:
        raise HTTPException(status_code=404, detail="not found")
    return {"id": m.id, "title": m.title, "genre": m.genre, "year": m.year,
            "rental_price": m.rental_price, "stock": m.stock}


# ---------------- Users ----------------

@app.get("/api/v1/users/{user_id}")
def get_user(user_id: int, db=Depends(db_session), auth=Depends(get_current_user)):
    # VULN 1: BOLA - any authenticated user can read ANY user_id's profile,
    # including balance/email, with no ownership check against auth['sub']
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="not found")
    return {"id": user.id, "username": user.username, "balance": user.balance,
            "is_admin": user.is_admin, "email": user.email}


class UserUpdateReq(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    balance: Optional[float] = None
    is_admin: Optional[bool] = None


@app.put("/api/v1/users/{user_id}")
def update_user(user_id: int, req: UserUpdateReq, db=Depends(db_session), auth=Depends(get_current_user)):
    # VULN 4: Mass Assignment - client can set balance / is_admin directly,
    # no allowlist of editable fields, no server-side ownership check either
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="not found")
    data = req.dict(exclude_unset=True)
    for k, v in data.items():
        setattr(user, k, v)
    db.commit()
    return {"id": user.id, "username": user.username, "balance": user.balance,
            "is_admin": user.is_admin, "email": user.email}


# ---------------- Rentals ----------------

class RentalReq(BaseModel):
    movie_id: int
    qty: int = 1


@app.post("/api/v1/rentals")
def create_rental(req: RentalReq, db=Depends(db_session), auth=Depends(get_current_user)):
    # VULN 5: Unrestricted Resource Consumption - no cap on qty, no real
    # balance/stock deduction check, lets a user rent 999999 copies for free
    movie = db.get(Movie, req.movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="movie not found")
    user_id = int(auth["sub"])
    rental = Rental(user_id=user_id, movie_id=req.movie_id, qty=req.qty)
    db.add(rental)
    db.commit()
    return {"id": rental.id, "movie_id": rental.movie_id, "qty": rental.qty,
            "total_price": movie.rental_price * req.qty}


@app.get("/api/v1/rentals")
def list_rentals(db=Depends(db_session), auth=Depends(get_current_user)):
    user_id = int(auth["sub"])
    rows = db.query(Rental).filter(Rental.user_id == user_id).all()
    return [{"id": r.id, "movie_id": r.movie_id, "qty": r.qty} for r in rows]


# ---------------- Snacks ----------------

@app.get("/api/v1/snacks")
def list_snacks(db=Depends(db_session)):
    rows = db.query(Snack).all()
    return [{"id": s.id, "name": s.name, "price": s.price, "stock": s.stock} for s in rows]


class SnackOrderReq(BaseModel):
    snack_id: int
    qty: int = 1


@app.post("/api/v1/snacks/order")
def order_snack(req: SnackOrderReq, db=Depends(db_session), auth=Depends(get_current_user)):
    # VULN 5 (cont.): Unrestricted qty again - no upper bound, no balance check
    snack = db.get(Snack, req.snack_id)
    if not snack:
        raise HTTPException(status_code=404, detail="snack not found")
    return {"snack": snack.name, "qty": req.qty, "total_price": snack.price * req.qty}


# ---------------- Admin ----------------

@app.get("/api/v1/admin/users")
def admin_list_users(db=Depends(db_session), auth=Depends(get_current_user)):
    # VULN 2: BFLA - checks only that a token exists/decodes, never verifies
    # auth['is_admin'] is True, so any valid user (or forged 'none' token)
    # reaches this admin-only function
    rows = db.query(User).all()
    return [{"id": u.id, "username": u.username, "balance": u.balance,
             "is_admin": u.is_admin, "email": u.email} for u in rows]


@app.delete("/api/v1/admin/users/{user_id}")
def admin_delete_user(user_id: int, db=Depends(db_session), auth=Depends(get_current_user)):
    # VULN 2 (cont.): same BFLA - no role check before a destructive action
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="not found")
    db.delete(user)
    db.commit()
    return {"deleted": user_id}
