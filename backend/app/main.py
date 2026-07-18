import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import engine, Base, SessionLocal
from app.models.document import Document
from app.models.user import User
from app.models.office import Office
from app.models.typology import Typology
from app.models.frazione import Frazione
from app.models.firmatario import Firmatario
from app.routers import auth, documents, audit
from app.routers.chat import router as chat_router
from app.routers.crud_entita import router_offices, router_typologies, router_frazioni, router_firmatari
from app.services.scheduler import start_scheduler, shutdown_scheduler

# ---------------------------------------------------------------------------
# 1. CREAZIONE SCHEMA DB
#
# SQLAlchemy legge tutti i modelli importati e crea le tabelle corrispondenti
# nel database se non esistono già. Se le tabelle ci sono, non fa nulla.
# Questo avviene ogni volta che il server si avvia.
# ---------------------------------------------------------------------------
Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# 2. MIGRAZIONI LEGGERE (ALTER TABLE)
#
# SQLite non supporta Alembic (il tool standard di migrazioni per SQLAlchemy)
# in modo nativo. Quando aggiungiamo nuove colonne al modello dopo il primo deploy,
# i database esistenti non le hanno ancora. Questa funzione le aggiunge manualmente
# con ALTER TABLE, controllando prima se la colonna è già presente.
# Solo per SQLite: altri database userebbero Alembic normalmente.
# ---------------------------------------------------------------------------
def run_migrations():
    # Eseguiamo solo su SQLite: gli altri DB vengono gestiti da strumenti migliori
    if not engine.url.drivername.startswith("sqlite"):
        print("Database non SQLite: migrazioni automatiche SQLite saltate.")
        return

    db: Session = SessionLocal()
    try:
        # PRAGMA table_info restituisce le colonne della tabella: lo usiamo per
        # vedere quali colonne esistono già prima di provare ad aggiungerle
        cursor = db.execute(text("PRAGMA table_info(documents)"))
        columns = [row[1] for row in cursor.fetchall()]

        # Aggiungiamo le colonne mancanti (quelle aggiunte dopo la prima versione)
        for col_name, col_def in [
            ("data_scadenza", "DATE NULL"),
            ("frazioni", "TEXT NULL"),
            ("stato_elaborazione", "VARCHAR(50) DEFAULT 'completato'"),
        ]:
            if col_name not in columns:
                db.execute(text(f"ALTER TABLE documents ADD COLUMN {col_name} {col_def}"))
                print(f"Migration: Aggiunta colonna {col_name}.")
        db.commit()
    except Exception as e:
        print(f"Errore durante le migrazioni del DB SQLite: {e}")
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Eseguito all'avvio del server
    run_migrations()
    start_scheduler()
    yield
    # Eseguito allo spegnimento del server
    shutdown_scheduler()

# ---------------------------------------------------------------------------
# 3. AUTO-SEEDING — Dati di default
#
# Al primo avvio il database è completamente vuoto. Questi seed inseriscono
# i dati di base (uffici comunali, tipologie, frazioni, account admin)
# per rendere il sistema immediatamente utilizzabile senza configurazione manuale.
# Il seed è idempotente: se i dati esistono già, non fa nulla.
# ---------------------------------------------------------------------------

def _seed_entita(model, nome_campo, valori_default, etichetta):
    """Inserisce i valori di default per un'entità se la sua tabella è vuota."""
    db: Session = SessionLocal()
    try:
        if db.query(model).count() == 0:
            for v in valori_default:
                db.add(model(**{nome_campo: v}))
            db.commit()
            print(f"Seed: {etichetta} di default creati.")
    except Exception as e:
        print(f"Errore seed {etichetta}: {e}")
    finally:
        db.close()

def seed_default_admin():
    """
    Crea l'utente 'admin' (Amministratore Supremo) se non esiste ancora.
    La password di default viene letta dalla variabile d'ambiente ADMIN_DEFAULT_PASSWORD
    o usa un fallback sicuro solo per lo sviluppo locale.
    """
    db: Session = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "admin").first():
            pwd = os.getenv("ADMIN_DEFAULT_PASSWORD", "admin_documatch_2026")
            from app.core.security import get_password_hash
            db.add(User(
                username="admin",
                hashed_password=get_password_hash(pwd)
            ))
            db.commit()
            print("Seed: Utente 'admin' creato.")
    except Exception as e:
        print(f"Errore seed admin: {e}")
    finally:
        db.close()

# Eseguiamo i seed all'avvio (sono tutti idempotenti)
seed_default_admin()
_seed_entita(Office, "nome", [
    "Ufficio Tecnico", "Ufficio Ambiente", "Polizia Locale",
    "Servizi Demografici", "Ufficio Tributi", "Servizi Sociali",
    "Segreteria Generale", "URP"
], "Uffici")
_seed_entita(Typology, "nome", [
    "Delibera di Giunta", "Delibera di Consiglio", "Determinazione Dirigenziale",
    "Ordinanza Sindacale", "Autorizzazione Paesaggistica", "Bando di Gara",
    "Regolamento Comunale", "Da Classificare"
], "Tipologie")
_seed_entita(Frazione, "nome", [
    "Capoluogo (Centro)", "Frazione Marina", "Frazione Collinare", "Zona Industriale"
], "Frazioni")
_seed_entita(Firmatario, "nome", [
    "Sindaco Mario Gentile", "Segretario Comunale Dott. Mancini", "Resp. UTC Ing. Rossi", "Resp. Edilizia Arch. Ferrara"
], "Firmatari")

# Assicuriamoci che la tipologia di fallback esista sempre, anche se il DB era già popolato
def _ensure_da_classificare():
    db: Session = SessionLocal()
    try:
        if not db.query(Typology).filter(Typology.nome == "Da Classificare").first():
            db.add(Typology(nome="Da Classificare"))
            db.commit()
            print("Seed: Aggiunta tipologia di fallback 'Da Classificare'.")
    except Exception as e:
        pass
    finally:
        db.close()

_ensure_da_classificare()

# ---------------------------------------------------------------------------
# 4. ISTANZA FASTAPI
#
# Creiamo l'applicazione FastAPI con i metadati che appaiono nella UI Swagger (/docs).
# ---------------------------------------------------------------------------
app = FastAPI(
    title="DocuMatch",
    description="Sistema Cloud per l'Archiviazione, Ricerca Vettoriale ed Estrazione OCR di Atti Comunali",
    version="1.0.0",
    lifespan=lifespan
)

# ---------------------------------------------------------------------------
# 5. MIDDLEWARE CORS
#
# CORS (Cross-Origin Resource Sharing) è un meccanismo di sicurezza del browser
# che blocca le richieste HTTP verso un dominio diverso da quello della pagina.
# Il frontend (es. su porta 5173) e il backend (porta 8000) hanno origini diverse,
# quindi senza questo middleware il browser bloccherebbe tutte le chiamate API.
#
# In produzione su Azure, CORS_ALLOWED_ORIGINS deve essere impostato con
# il dominio esatto del frontend (es. "https://documatch.azurewebsites.net")
# per evitare di accettare richieste da qualsiasi sito web.
# ---------------------------------------------------------------------------
_cors_env = os.getenv("CORS_ALLOWED_ORIGINS", "*")
if os.getenv("ENVIRONMENT") == "production" and _cors_env == "*":
    raise Exception("CRITICO: In produzione CORS_ALLOWED_ORIGINS non può essere '*'. Imposta il dominio esatto del frontend.")

_cors_origins = ["*"] if _cors_env == "*" else [o.strip() for o in _cors_env.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# 6. ROUTER — Montaggio delle aree funzionali dell'API
#
# Registriamo tutti i router: ogni router gestisce una sezione dell'API.
# I prefissi URL sono definiti all'interno di ciascun router.
# ---------------------------------------------------------------------------
app.include_router(auth.router)            # /api/v1/auth/*
app.include_router(audit.router, prefix="/api/v1")
app.include_router(documents.router)       # /api/v1/documents/*
app.include_router(chat_router)            # /api/v1/chat/*
app.include_router(router_offices)         # /api/v1/offices/*
app.include_router(router_typologies)      # /api/v1/typologies/*
app.include_router(router_frazioni)        # /api/v1/frazioni/*
app.include_router(router_firmatari)       # /api/v1/firmatari/*

# ---------------------------------------------------------------------------
# 7. FILE STATICI — Immagini caricate tramite OCR
#
# Montiamo la cartella app/static/ come directory di file statici serviti
# direttamente da FastAPI sotto il path /static. Questo permette al frontend
# di visualizzare le immagini caricate in modalità locale con un URL diretto.
# In produzione, i file vanno su Azure Blob Storage (URL diverso).
# ---------------------------------------------------------------------------
os.makedirs("app/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ---------------------------------------------------------------------------
# 8. ENDPOINT ROOT — Health Check
#
# Un endpoint semplice per verificare che il backend sia attivo e funzionante.
# Utile per i load balancer e i sistemi di monitoraggio di Azure.
# ---------------------------------------------------------------------------
@app.get("/")
def read_root():
    return {
        "status": "healthy",
        "project": "DocuMatch",
    }

# touch for reload
