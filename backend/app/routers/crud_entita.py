"""
Router CRUD generico per entità "nome" (Uffici, Tipologie, Frazioni).

Le tre entità condividono la stessa struttura (id + nome), gli stessi endpoint
CRUD e la stessa logica di autorizzazione. Invece di scrivere tre volte lo
stesso codice (150+ righe per ogni entità), questo modulo usa una "factory function"
che genera un router FastAPI completo a partire dai parametri specifici dell'entità.

⚠️ PUNTO CRITICO: questo è il pattern DRY (Don't Repeat Yourself) applicato
ai router FastAPI. Se in futuro si vuole cambiare il comportamento del CRUD
(es. aggiungere un log delle modifiche), lo si fa in un posto solo.
"""
import json
from typing import List, Optional, Callable
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.models.document import Document
from app.core.security import get_current_admin

# Import dei modelli e schemi delle tre entità che condividono questo router
from app.models.office import Office
from app.models.typology import Typology
from app.models.frazione import Frazione
from app.schemas.office import OfficeCreate, OfficeResponse
from app.schemas.typology import TypologyCreate, TypologyResponse
from app.schemas.frazione import FrazioneCreate, FrazioneResponse
from app.models.firmatario import Firmatario
from app.schemas.firmatario import FirmatarioCreate, FirmatarioResponse


# =============================================================================
# Strategie di propagazione ai documenti
#
# Quando un'entità viene rinominata o eliminata, i documenti che la referenziano
# devono essere aggiornati di conseguenza. Ogni entità ha una strategia diversa
# perché i dati sono salvati in formati diversi nel DB.
# =============================================================================

def _propaga_lista_json(db: Session, campo_doc: str, old_name: str, new_name: Optional[str]):
    """
    Aggiorna i documenti in cui l'entità è salvata come elemento di una lista JSON.
    Usata per gli UFFICI (salvati come '["Ufficio Tecnico", "Ufficio Ambiente"]').

    Se new_name è None → rimuove l'ufficio dalla lista (caso eliminazione).
    Se new_name è una stringa → rinomina l'ufficio nella lista (caso modifica).
    """
    for doc in db.query(Document).all():
        raw = getattr(doc, campo_doc)
        if not raw:
            continue
        try:
            lista = json.loads(raw)
        except Exception:
            continue  # Se il JSON è corrotto, saltiamo il documento
        if old_name not in lista:
            continue   # Questo documento non usa l'entità modificata

        if new_name is None:
            # Eliminazione: rimuoviamo l'entità dalla lista
            lista = [x for x in lista if x != old_name]
        else:
            # Rinomina: sostituiamo il vecchio nome con il nuovo
            lista = [new_name if x == old_name else x for x in lista]
        setattr(doc, campo_doc, json.dumps(lista))


def _propaga_colonna_stringa(db: Session, campo_doc: str, old_name: str, new_name: Optional[str]):
    """
    Aggiorna i documenti in cui l'entità è salvata come stringa semplice.
    Usata per TIPOLOGIA e FRAZIONE (salvati come singola stringa, es. "Delibera di Giunta").

    Se new_name è None → imposta il campo a NULL (caso eliminazione).
    Se new_name è una stringa → aggiorna il valore (caso rinomina).

    Usa un UPDATE SQL diretto invece di caricare tutti i documenti in memoria:
    più efficiente con molti documenti.
    """
    db.query(Document).filter(
        getattr(Document, campo_doc) == old_name
    ).update({getattr(Document, campo_doc): new_name})


def _propaga_tipologia_elimina(db: Session, campo_doc: str, old_name: str, _new_name: Optional[str]):
    """
    Quando una tipologia viene eliminata dal dizionario, non modifichiamo i documenti.
    In questo modo, la vecchia tipologia rimane come stringa nel documento, e la
    prossima volta che verrà modificato/importato, verrà rilevata come "entità mancante",
    attivando il normale flusso di risoluzione (NewEntityDialog).
    """
    pass


# =============================================================================
# Factory del router CRUD
#
# Questa funzione genera un APIRouter completo (GET lista, POST crea,
# PUT modifica, DELETE elimina) per qualsiasi entità con struttura {id, nome}.
# =============================================================================

def crea_router_entita(
    *,
    prefix: str,
    tag: str,
    etichetta: str,
    model,
    schema_create,
    schema_response,
    campo_doc: str,
    propaga_rinomina: Callable,
    propaga_elimina: Callable,
    proteggi_nome: Optional[str] = None,
) -> APIRouter:
    """
    Genera un APIRouter FastAPI completo per un'entità {id, nome}.

    Args:
        prefix/tag         — prefix URL e tag Swagger (es. "/api/v1/offices", "Offices")
        etichetta          — nome leggibile per i messaggi di errore (es. "ufficio")
        model              — classe SQLAlchemy (es. Office)
        schema_create/resp — schemi Pydantic per input e output
        campo_doc          — nome del campo in Document da aggiornare (es. "uffici")
        propaga_rinomina   — funzione da chiamare quando si rinomina l'entità
        propaga_elimina    — funzione da chiamare quando si elimina l'entità
        proteggi_nome      — nome che non può essere modificato/eliminato (es. "Altro")
    """
    router = APIRouter(prefix=prefix, tags=[tag])

    # --- GET / — Lista tutte le entità ordinate alfabeticamente ---
    @router.get("/", response_model=List[schema_response])
    def lista(db: Session = Depends(get_db)):
        # Endpoint pubblico: non richiede autenticazione (serve anche ai filtri della vista pubblica)
        return db.query(model).order_by(model.nome.asc()).all()

    # --- POST / — Crea una nuova entità ---
    @router.post("/", response_model=schema_response, status_code=status.HTTP_201_CREATED)
    def crea(payload: schema_create, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
        nome = payload.nome.strip()
        if not nome:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Il nome non può essere vuoto.")
            
        # Se l'entità esiste già (anche con maiuscole/minuscole diverse), la restituiamo direttamente 
        # senza creare duplicati o lanciare errori.
        esistente = db.query(model).filter(func.lower(model.nome) == func.lower(nome)).first()
        if esistente:
            return esistente
            
        obj = model(nome=nome)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # --- PUT /{item_id} — Rinomina un'entità esistente ---
    @router.put("/{item_id}", response_model=schema_response)
    def modifica(item_id: int, payload: schema_create, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
        obj = db.query(model).filter(model.id == item_id).first()
        if not obj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"{etichetta.capitalize()} non trovato/a.")
        old_name = obj.nome
        new_name = payload.nome.strip()
        if not new_name:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Il nome non può essere vuoto.")
        # Blocchiamo la rinomina delle entità protette (es. "Altro" per le tipologie)
        if proteggi_nome and old_name.lower() == proteggi_nome.lower() and new_name.lower() != proteggi_nome.lower():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"'{proteggi_nome}' non può essere rinominato/a.")
        # Verifichiamo che il nuovo nome non sia già preso da un'altra entità
        dup = db.query(model).filter(model.nome == new_name).first()
        if dup and dup.id != item_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"'{new_name}' è già presente nel database.")
        obj.nome = new_name
        # Propaghiamo la rinomina a tutti i documenti che usavano il vecchio nome
        propaga_rinomina(db, campo_doc, old_name, new_name)
        db.commit()
        db.refresh(obj)
        return obj

    # --- DELETE /{item_id} — Elimina un'entità ---
    @router.delete("/{item_id}", status_code=status.HTTP_200_OK)
    def elimina(item_id: int, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
        obj = db.query(model).filter(model.id == item_id).first()
        if not obj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"{etichetta.capitalize()} non trovato/a.")
        nome = obj.nome
        # Blocchiamo l'eliminazione delle entità protette (es. "Altro")
        if proteggi_nome and nome.lower() == proteggi_nome.lower():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"'{proteggi_nome}' non può essere eliminato/a.")
        # Verifica se l'entità è associata a qualche documento
        in_use = False
        if campo_doc in ["tipologia", "frazione"]:
            in_use = db.query(Document).filter(getattr(Document, campo_doc) == nome).first() is not None
        else:
            # Per i campi JSON (uffici, firmatari) facciamo un controllo con LIKE e validazione
            docs = db.query(Document).filter(getattr(Document, campo_doc).like(f'%"{nome}"%')).all()
            for doc in docs:
                raw = getattr(doc, campo_doc)
                if raw:
                    try:
                        lista = json.loads(raw)
                        if nome in lista:
                            in_use = True
                            break
                    except:
                        pass
        
        if in_use:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Impossibile eliminare {etichetta} '{nome}' perché è associato a uno o più documenti.")

        # Non propaghiamo l'eliminazione, rimuoviamo e basta
        db.delete(obj)
        db.commit()
        return {"status": "success", "messaggio": f"{etichetta.capitalize()} '{nome}' rimosso/a correttamente."}

    return router


# =============================================================================
# Istanziazione dei tre router concreti
#
# Qui la factory viene chiamata tre volte con i parametri specifici di ogni entità.
# Il risultato sono tre router FastAPI pronti da registrare in main.py.
# =============================================================================

# Router per gli Uffici Comunali
# Gli uffici sono salvati come lista JSON nei documenti → usiamo _propaga_lista_json
router_offices = crea_router_entita(
    prefix="/api/v1/offices",
    tag="Offices",
    etichetta="ufficio",
    model=Office,
    schema_create=OfficeCreate,
    schema_response=OfficeResponse,
    campo_doc="uffici",
    propaga_rinomina=_propaga_lista_json,
    propaga_elimina=lambda db, campo, old, new: _propaga_lista_json(db, campo, old, None),
)

# Router per le Tipologie Documentali
# Le tipologie sono salvate come stringa semplice → usiamo _propaga_colonna_stringa
router_typologies = crea_router_entita(
    prefix="/api/v1/typologies",
    tag="Typologies",
    etichetta="tipologia",
    model=Typology,
    schema_create=TypologyCreate,
    schema_response=TypologyResponse,
    campo_doc="tipologia",
    propaga_rinomina=_propaga_colonna_stringa,
    propaga_elimina=_propaga_tipologia_elimina,
)

# Router per le Frazioni Comunali
# Le frazioni sono salvate come stringa semplice → usiamo _propaga_colonna_stringa
router_frazioni = crea_router_entita(
    prefix="/api/v1/frazioni",
    tag="Frazioni",
    etichetta="frazione",
    model=Frazione,
    schema_create=FrazioneCreate,
    schema_response=FrazioneResponse,
    campo_doc="frazioni",
    propaga_rinomina=_propaga_lista_json,
    propaga_elimina=lambda db, campo, old, new: _propaga_lista_json(db, campo, old, None),
)

# Router per i Firmatari
# I firmatari sono salvati come lista JSON nei documenti → usiamo _propaga_lista_json
router_firmatari = crea_router_entita(
    prefix="/api/v1/firmatari",
    tag="Firmatari",
    etichetta="firmatario",
    model=Firmatario,
    schema_create=FirmatarioCreate,
    schema_response=FirmatarioResponse,
    campo_doc="firmatari",
    propaga_rinomina=_propaga_lista_json,
    propaga_elimina=lambda db, campo, old, new: _propaga_lista_json(db, campo, old, None),
)

