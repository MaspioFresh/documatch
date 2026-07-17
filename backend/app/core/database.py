import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# ---------------------------------------------------------------------------
# Configurazione URL del database
#
# In sviluppo locale usiamo SQLite: un semplice file .db sulla macchina,
# zero configurazione, zero server da avviare.
# In produzione su Azure basta impostare la variabile d'ambiente DATABASE_URL
# con la stringa di connessione al database Azure (es. PostgreSQL o Azure SQL)
# e tutto il resto del codice funziona senza alcuna modifica.
# ---------------------------------------------------------------------------
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./documatch.db")

# SQLite ha un limite: di default consente l'accesso da un solo thread alla volta.
# FastAPI gestisce più richieste in parallelo su thread diversi, quindi dobbiamo
# disabilitare questo controllo. Per gli altri database (PostgreSQL, ecc.)
# questo parametro non serve e viene omesso.
is_sqlite = SQLALCHEMY_DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

# Creiamo il "motore" SQLAlchemy: è il punto di contatto tra Python e il database.
# Ogni operazione DB passa da qui.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args=connect_args
)

# SessionLocal è la "fabbrica" di sessioni DB.
# autocommit=False → le modifiche non vengono salvate automaticamente,
#                    dobbiamo chiamare db.commit() esplicitamente (più controllo sugli errori)
# autoflush=False  → SQLAlchemy non manda query intermedie al DB prima del commit
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base è la classe madre da cui ereditano tutti i modelli SQLAlchemy del progetto.
# SQLAlchemy usa questa classe per sapere quali tabelle creare nel database.
class Base(DeclarativeBase):
    pass

# ---------------------------------------------------------------------------
# get_db — Dependency Injection per la sessione database
#
# Questa funzione viene usata con Depends(get_db) negli endpoint FastAPI.
# Il "yield" la trasforma in un generatore: FastAPI chiama get_db(), ottiene
# la sessione, la passa all'endpoint, e quando l'endpoint finisce (bene o male)
# esegue il blocco "finally" che chiude la connessione.
# In questo modo non rischiamo mai di lasciare connessioni aperte nel database.
# ---------------------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db        # Qui FastAPI "sospende" get_db e usa la sessione nell'endpoint
    finally:
        db.close()      # Questo blocco viene sempre eseguito, anche in caso di eccezione
