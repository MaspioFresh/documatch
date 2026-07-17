import uuid
from sqlalchemy import Column, String, Integer
from app.core.database import Base

# ---------------------------------------------------------------------------
# Modello User — Rappresenta un operatore/amministratore del sistema
#
# Questa classe dice a SQLAlchemy come costruire la tabella "users" nel database.
# Ogni istanza di User corrisponde a una riga nella tabella.
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    # UUID come chiave primaria: usiamo una stringa invece di un intero auto-incrementale
    # perché gli UUID sono globalmente unici e non prevedibili (un attaccante
    # non può indovinare l'ID di un altro utente provando 1, 2, 3...).
    # La lambda genera automaticamente un nuovo UUID ad ogni creazione di utente.
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Username univoco e indicizzato: l'indice permette ricerche rapide per username
    # senza scansionare tutta la tabella (importante per il login).
    username = Column(String(150), unique=True, index=True, nullable=False)

    # La password NON viene mai salvata in chiaro: salviamo solo il suo hash bcrypt.
    # bcrypt include automaticamente un "salt" casuale per ogni hash, rendendo impossibile
    # l'uso di rainbow tables. L'hashing è gestito da passlib (CryptContext) in security.py.
    hashed_password = Column(String(255), nullable=False)

    # Email dell'operatore, opzionale: serve per inviare il link di reset password.
    # È nullable per retro-compatibilità con account creati prima che il campo esistesse.
    email = Column(String(255), nullable=True)

    # Token monouso per il reset password: viene generato quando si richiede il reset
    # e azzerato dopo l'uso (non può essere riutilizzato).
    # L'indice permette di trovare rapidamente l'utente dato il token (usato in /reset-password).
    reset_token = Column(String(100), index=True, nullable=True)

    # Timestamp UNIX (secondi dall'1/1/1970) che indica quando il token di reset scade.
    # Il reset è valido per 15 minuti dalla generazione.
    reset_token_expiry = Column(Integer, nullable=True)
