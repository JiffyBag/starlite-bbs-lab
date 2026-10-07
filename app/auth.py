import jwt
from fastapi import Header, HTTPException

# VULN 6: JWT weak secret + 'none' algorithm accepted on verify
SECRET = "starlite1985"


def create_token(user_id: int, username: str, is_admin: bool):
    payload = {"sub": str(user_id), "username": username, "is_admin": is_admin}
    return jwt.encode(payload, SECRET, algorithm="HS256")


def decode_token(token: str):
    # VULN 6: accepting 'none' alongside HS256 lets an attacker forge an
    # unsigned token (alg=none) and bypass signature verification entirely.
    return jwt.decode(token, SECRET, algorithms=["HS256", "none"])


def get_current_user(authorization: str = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload
