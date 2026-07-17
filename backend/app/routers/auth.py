import hashlib
import time
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    ForgotPasswordRequest,
    ConfirmResetPasswordRequest
)
from app.core.security import generate_token, get_current_admin, verify_password, get_password_hash
from app.services.email import email_service

# ---------------------------------------------------------------------------
# Router di autenticazione
#
# Raggruppa tutti gli endpoint legati alla gestione degli account e delle sessioni.
# Il prefisso /api/v1/auth viene anteposto a tutte le route definite qui sotto.
# ---------------------------------------------------------------------------
router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"]
)


# ---------------------------------------------------------------------------
# Helper interno — Verifica che il chiamante sia l'Amministratore Supremo
#
# Molti endpoint sono riservati all'utente "admin" (Amministratore Supremo),
# non a qualsiasi operatore autenticato. Questo helper centralizza il controllo.
# ---------------------------------------------------------------------------
def _richiedi_admin_supremo(admin_username: str):
    if admin_username != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operazione riservata esclusivamente all'Amministratore Supremo dell'ente."
        )

# ---------------------------------------------------------------------------
# POST /login
#
# Endpoint pubblico (nessuna autenticazione richiesta).
# Verifica le credenziali e, se corrette, emette un Bearer Token di sessione.
# ---------------------------------------------------------------------------
@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Verifica username e password, restituisce un token di sessione in caso di successo.
    """
    # Cerchiamo l'utente nel database per username
    user = db.query(User).filter(User.username == payload.username).first()

    # ⚠️ PUNTO CRITICO: usiamo lo stesso messaggio di errore sia per "utente non trovato"
    # che per "password sbagliata". Se i messaggi fossero diversi, un attaccante
    # potrebbe capire quali username esistono nel sistema (username enumeration).
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenziali non valide. Controlla username e password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verifichiamo la password in chiaro contro l'hash bcrypt salvato
    if verify_password(payload.password, user.hashed_password):
        token = generate_token(user.username)
        return TokenResponse(
            access_token=token,
            username=user.username
        )

    # Password errata: stesso messaggio generico per evitare username enumeration
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenziali non valide. Controlla username e password.",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Richiede il link di ripristino password per un utente.
    Se l'utente esiste e ha un'email configurata, viene generato un token e inviato via email.
    """
    user = db.query(User).filter(User.username == payload.username).first()
    
    # ⚠️ PUNTO CRITICO: Rispondiamo sempre con lo stesso messaggio per evitare
    # la potenziale enumerazione degli account validi.
    success_message = {"message": "Se l'utente esiste ed ha un'email configurata, riceverà a breve le istruzioni per il reset."}
    
    if not user or not user.email:
        return success_message
        
    # Generiamo un token sicuro e la sua scadenza (15 minuti)
    token = str(uuid.uuid4())
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires = int(time.time()) + (15 * 60)
    
    # Salviamo SOLO L'HASH nel database (non in chiaro)
    user.reset_token = token_hash
    user.reset_token_expiry = expires
    db.commit()
    
    # Invia l'email in background o sincrona
    email_service.invia_email_reset(user.email, user.username, token)
    
    return success_message


@router.post("/reset-password")
def reset_password(payload: ConfirmResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Imposta una nuova password utilizzando il token ricevuto via email.
    """
    # Calcoliamo l'hash del token fornito per confrontarlo con quello salvato nel DB
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    
    # Cerchiamo l'utente tramite l'hash del token
    user = db.query(User).filter(User.reset_token == token_hash).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token non valido o inesistente."
        )
        
    # Verifichiamo che il token non sia scaduto
    import time
    if not user.reset_token_expiry or time.time() > user.reset_token_expiry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Il token di reset è scaduto. Richiedi un nuovo ripristino password."
        )
        
    # Aggiorniamo la password utilizzando Bcrypt (tramite la nostra funzione di sicurezza)
    user.hashed_password = get_password_hash(payload.password)
    
    # Invalidiamo il token per evitare riutilizzi
    user.reset_token = None
    user.reset_token_expiry = None
    
    db.commit()
    
    return {"message": "Password aggiornata con successo! Ora puoi effettuare il login."}

# ---------------------------------------------------------------------------
# Endpoint di Gestione Utenti (Riservati all'Admin Supremo)
# ---------------------------------------------------------------------------

from typing import List
from app.schemas.auth import RegisterRequest, UserResponse


@router.get("/users", response_model=List[UserResponse])
def get_users(db: Session = Depends(get_db), current_admin: str = Depends(get_current_admin)):
    """Restituisce la lista di tutti gli utenti. Solo l'admin supremo può vederla."""
    _richiedi_admin_supremo(current_admin)
    users = db.query(User).all()
    return users

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: RegisterRequest, db: Session = Depends(get_db), current_admin: str = Depends(get_current_admin)):
    """Crea un nuovo utente (sotto-admin) inviandogli un invito via email. Solo l'admin supremo può farlo."""
    _richiedi_admin_supremo(current_admin)
    
    # Controlla se l'utente esiste già
    existing_user = db.query(User).filter(User.username == payload.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username già in uso."
        )
    
    # Genera una password temporanea inusabile (l'utente imposterà la sua)
    temp_password = str(uuid.uuid4())
    
    # Genera il token di invito (valido 2 ore)
    token = str(uuid.uuid4())
    import hashlib
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires = int(time.time()) + (2 * 3600)
    
    new_user = User(
        username=payload.username,
        hashed_password=get_password_hash(temp_password),
        email=payload.email,
        reset_token=token_hash,
        reset_token_expiry=expires
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Invia email di invito
    email_service.invia_email_invito(new_user.email, new_user.username, token)
    
    return new_user

@router.delete("/users/{username}")
def delete_user(username: str, db: Session = Depends(get_db), current_admin: str = Depends(get_current_admin)):
    """Elimina un utente dal sistema."""
    _richiedi_admin_supremo(current_admin)
    
    if username == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Non è possibile eliminare l'Amministratore Supremo."
        )
        
    user_to_delete = db.query(User).filter(User.username == username).first()
    if not user_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utente non trovato."
        )
        
    db.delete(user_to_delete)
    db.commit()
    return {"message": f"Utente {username} eliminato con successo."}

@router.post("/trigger-expiration-check")
def trigger_expiration_check(current_admin: str = Depends(get_current_admin)):
    """Forza l'esecuzione del cron job di controllo scadenze (per scopi di demo/debug)."""
    _richiedi_admin_supremo(current_admin)
    from app.services.scheduler import check_expiring_documents
    try:
        check_expiring_documents(force_all_upcoming=True)
        return {"message": "Controllo scadenze forzato con successo. Verifica la cartella mock_emails o la tua casella di posta."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
