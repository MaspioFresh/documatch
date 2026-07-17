import os
import time
from typing import Optional
from fastapi import Header, HTTPException, status
import jwt
from passlib.context import CryptContext

# ---------------------------------------------------------------------------
# SECRET_KEY — La chiave segreta per firmare i token
# ---------------------------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "documatch_super_secret_key_for_signing_tokens_2026")
ALGORITHM = "HS256"

# Controllo critico di sicurezza per la produzione
if os.getenv("ENVIRONMENT") == "production" and SECRET_KEY == "documatch_super_secret_key_for_signing_tokens_2026":
    raise Exception("CRITICO: Stai avviando in produzione con la SECRET_KEY di default. Imposta una chiave sicura!")

_expire_hours = int(os.getenv("SESSION_EXPIRE_HOURS", "8"))
TOKEN_EXPIRE_SECONDS = 3600 * _expire_hours

# Passlib CryptContext per Hashing Bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica che la password in chiaro corrisponda all'hash bcrypt."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Genera un hash bcrypt sicuro dalla password in chiaro (include salt automatico)."""
    return pwd_context.hash(password)

def generate_token(username: str) -> str:
    """Genera un JWT firmato con HMAC-SHA256 usando PyJWT."""
    expire_time = time.time() + TOKEN_EXPIRE_SECONDS
    payload = {
        "sub": username,
        "exp": expire_time
    }
    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[str]:
    """Verifica la validità del JWT e ne estrae il payload (username)."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except jwt.ExpiredSignatureError:
        return None  # Token scaduto
    except jwt.InvalidTokenError:
        return None  # Token contraffatto o manomesso

def get_current_admin(authorization: Optional[str] = Header(None)) -> str:
    """Dipendenza FastAPI per estrarre e verificare l'Admin dal token."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token di autenticazione mancante. Accesso negato.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        token_type, token = authorization.split(" ", 1)
        if token_type.lower() != "bearer":
            raise ValueError()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Formato header Authorization non valido. Usa 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = verify_token(token)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token scaduto o non valido. Effettua nuovamente il login.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return username
