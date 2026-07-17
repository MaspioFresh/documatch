import csv
import io
import json
import os
import zipfile
import datetime
import pandas as pd
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from app.core.database import get_db, SessionLocal
from app.models.document import Document
from app.models.office import Office
from app.models.typology import Typology
from app.models.frazione import Frazione
from app.models.firmatario import Firmatario
from app.schemas.document import DocumentCreate, DocumentResponse, BulkActionRequest
from app.core.security import get_current_admin

from app.models.audit import AuditLog


# Importiamo i servizi AI, NLP e Storage
# Ogni servizio ha una modalità "reale" (Azure) e una "mock" (locale):
# il codice è identico indipendentemente dalla modalità attiva.
from app.services.nlp import (
    elabora_testo_nlp,
    genera_embedding,
    cerca_documenti_simili,
    calcola_similarita_coseno,
    spiega_similarita_semantica,
    spiega_similarita_ricerca
)
from app.services.storage import storage_service
from app.services.ocr import ocr_service
from app.services.generative_ai import estrai_metadati_da_ocr

router = APIRouter(
    prefix="/api/v1/documents",
    tags=["Documents"]
)

# =============================================================================
# map_db_to_schema — Serializzazione DB → Schema Pydantic
#
# Il modello SQLAlchemy salva uffici, firmatari ed embedding come stringhe JSON
# (es. uffici = '["Ufficio Tecnico", "URP"]'). Pydantic si aspetta invece
# i tipi Python corretti (List[str], List[float]).
# Questa funzione fa la conversione esplicita con gestione degli errori.
#
# Nota: non usiamo from_attributes direttamente perché SQLAlchemy restituirebbe
# la stringa grezza, non la lista deserializzata.
# =============================================================================
def map_db_to_schema(db_doc: Document) -> DocumentResponse:
    """Converte un oggetto Document SQLAlchemy in uno schema DocumentResponse Pydantic."""
    try:
        uffici_list = json.loads(db_doc.uffici) if db_doc.uffici else []
    except Exception:
        uffici_list = []  # Se il JSON è corrotto, usiamo una lista vuota

    try:
        firmatari_list = json.loads(db_doc.firmatari) if db_doc.firmatari else []
    except Exception:
        firmatari_list = []

    try:
        emb = json.loads(db_doc.embedding) if db_doc.embedding else None
    except Exception:
        emb = None

    try:
        frazioni_list = json.loads(db_doc.frazioni) if db_doc.frazioni else []
    except Exception:
        frazioni_list = []

    img_url = db_doc.url_immagine
    if img_url:
        # Se contiene /static/, teniamo solo la parte da /static/ in poi (rimuove domini vecchi)
        if "/static/" in img_url:
            img_url = "/static/" + img_url.split("/static/", 1)[1]
        # Se è un url esterno o assoluto strano che non contiene /static/
        elif img_url.startswith("http"):
            pass 
        # Se è solo il nome del file (es: "documento.png") o manca il percorso iniziale
        elif not img_url.startswith("/"):
            # Probabilmente è solo il basename a causa di vecchie importazioni
            img_basename = img_url.split("/")[-1]
            img_url = f"/static/uploads/{img_basename}"

    return DocumentResponse(
        id=db_doc.id,
        nome=db_doc.nome,
        descrizione=db_doc.descrizione,
        tipologia=db_doc.tipologia,
        data=db_doc.data,
        uffici=uffici_list,
        firmatari=firmatari_list,
        url_immagine=img_url,
        testo_estratto=db_doc.testo_estratto,
        embedding=emb,
        data_scadenza=db_doc.data_scadenza,
        frazioni=frazioni_list,
        stato_elaborazione=getattr(db_doc, "stato_elaborazione", "completato")
    )


def _filtra_per_campo_lista_json(docs, campo: str, valori, logica: str, wildcard: str = None):
    """
    Filtra una lista di documenti per un campo salvato come lista JSON.
    Usato per uffici e firmatari, dove il campo contiene più valori.

    logica="and" → il documento deve contenere TUTTI i valori cercati
    logica="or"  → il documento deve contenere ALMENO UN valore cercato
    
    wildcard → se specificato (es. 'tutte le frazioni'), i documenti che contengono
               questo valore vengono sempre inclusi, a prescindere dal filtro.

    La ricerca è parziale (substring): "Tecnico" trova "Ufficio Tecnico".
    """
    valori_clean = [v.lower().strip() for v in valori if v and v.strip()]
    if not valori_clean:
        return docs
    cmp = all if logica.lower() == "and" else any
    filtrati = []
    for d in docs:
        try:
            lista = json.loads(getattr(d, campo) or "[]")
        except Exception:
            lista = []
        lista_lower = [x.lower().strip() for x in lista]
        
        # Se il documento possiede la wildcard, bypassa i filtri e includilo sempre
        if wildcard and wildcard.lower() in lista_lower:
            filtrati.append(d)
            continue
            
        if cmp(any(vc in x for x in lista_lower) for vc in valori_clean):
            filtrati.append(d)
    return filtrati


# =============================================================================
# ENDPOINT PUBBLICI — Consultazione Archivio Cittadini
# Questi endpoint non richiedono autenticazione: sono visibili a tutti.
# =============================================================================

@router.get("/", response_model=List[DocumentResponse])
def get_all_documents(db: Session = Depends(get_db)):
    """Restituisce la lista completa di tutti i documenti in archivio."""
    db_docs = db.query(Document).all()
    return [map_db_to_schema(doc) for doc in db_docs]


@router.get("/search")
def search_documents_semantically(
    query_testo: str = Query(..., description="Testo da cercare per affinità semantica"),
    tipologia: Optional[List[str]] = Query(None, description="Filtri per tipologia dell'atto"),
    tipologia_logic: str = Query("or", description="Logica per tipologia (and/or)"),
    data_inizio: Optional[str] = Query(None, description="Data inizio (YYYY-MM-DD)"),
    data_fine: Optional[str] = Query(None, description="Data fine (YYYY-MM-DD)"),
    ufficio: Optional[List[str]] = Query(None, description="Filtri per dipartimento o ufficio"),
    ufficio_logic: str = Query("or", description="Logica per ufficio (and/or)"),
    firmatario: Optional[List[str]] = Query(None, description="Filtri per firmatario dell'atto"),
    firmatario_logic: str = Query("or", description="Logica di filtro per firmatari: 'and' o 'or'"),
    frazione: Optional[List[str]] = Query(None, description="Filtra per frazione (selezioni multiple)"),
    frazione_logic: str = Query("or", description="Logica di filtro per frazioni: 'and' o 'or'"),
    escludi_scaduti: bool = Query(False, description="Se true, non restituisce i documenti con data_scadenza passata"),
    db: Session = Depends(get_db)
):
    """
    Ricerca semantica vettoriale con filtri opzionali per metadati.

    Flusso:
    1. Si caricano tutti i documenti dal DB
    2. Si applicano i filtri per metadati (tipologia, date, uffici, ecc.)
    3. Si converte la query testuale in un vettore (embedding)
    4. Si calcola la similarità coseno tra il vettore query e i vettori dei documenti filtrati
    5. Si restituiscono i 5 documenti più simili con punteggio e spiegazione AI

    ⚠️ PUNTO CRITICO: la ricerca semantica è "per significato", non per parole esatte.
    "manutenzione strade" trova documenti che parlano di "rifacimento asfalto" anche
    senza avere le stesse parole.
    """
    tutti_i_documenti = db.query(Document).all()

    # Filtro 1: Tipologia — corrispondenza esatta case-insensitive
    if tipologia:
        tipologie_clean = [t.lower().strip() for t in tipologia if t and t.strip()]
        if tipologie_clean:
            if tipologia_logic.lower() == "and":
                tutti_i_documenti = [d for d in tutti_i_documenti if all(d.tipologia.lower() == t for t in tipologie_clean)]
            else:
                tutti_i_documenti = [d for d in tutti_i_documenti if any(d.tipologia.lower() == t for t in tipologie_clean)]

    # Filtro 2: Range di date — documenti emessi nell'intervallo specificato
    if data_inizio and data_inizio.strip():
        try:
            di = datetime.datetime.strptime(data_inizio.strip(), "%Y-%m-%d").date()
            tutti_i_documenti = [d for d in tutti_i_documenti if d.data >= di]
        except ValueError:
            pass  # Data malformata: ignoriamo il filtro

    if data_fine and data_fine.strip():
        try:
            df = datetime.datetime.strptime(data_fine.strip(), "%Y-%m-%d").date()
            tutti_i_documenti = [d for d in tutti_i_documenti if d.data <= df]
        except ValueError:
            pass

    # Filtro 3 & 4: Uffici e Firmatari — ricerca parziale (substring) nella lista JSON
    if ufficio:
        tutti_i_documenti = _filtra_per_campo_lista_json(tutti_i_documenti, "uffici", ufficio, ufficio_logic)

    if firmatario:
        tutti_i_documenti = _filtra_per_campo_lista_json(tutti_i_documenti, "firmatari", firmatario, firmatario_logic)

    # Filtro 5: Frazione — usando la logica JSON
    if frazione:
        tutti_i_documenti = _filtra_per_campo_lista_json(
            tutti_i_documenti, 
            "frazioni", 
            frazione, 
            frazione_logic,
            wildcard="tutte le frazioni"
        )

    # Filtro 6: Escludi scaduti — documenti con data_scadenza passata
    if escludi_scaduti:
        oggi = datetime.date.today()
        tutti_i_documenti = [d for d in tutti_i_documenti if not d.data_scadenza or d.data_scadenza >= oggi]

    # Ricerca vettoriale: convertiamo la query in embedding e cerchiamo i più simili
    vettore_query = genera_embedding(query_testo)
    simili = cerca_documenti_simili(vettore_query, tutti_i_documenti, limite=5, query_testo=query_testo)

    risultati = []
    for doc, score in simili:
        risultati.append({
            "documento": map_db_to_schema(doc),
            "punteggio_similarita": round(min(score, 0.99), 3),  # Cap a 0.99 per realismo
            "spiegazione_ia": None
        })

    return risultati


@router.post("/search-by-image")
def search_documents_by_image(
    file: UploadFile = File(..., description="Foto della prima pagina dell'atto per ricerca OCR"),
    db: Session = Depends(get_db)
):
    """
    Ricerca per immagine: carica la foto di un atto, estrae il testo via OCR,
    calcola l'embedding e trova i documenti simili nell'archivio.

    Utile quando il cittadino ha in mano una copia cartacea di un atto
    e vuole trovarne la versione digitale nell'archivio.
    """
    # 1. Estraiamo il testo dall'immagine tramite OCR (Azure o mock locale)
    testo_estratto = ocr_service.estrai_testo(file)

    if not testo_estratto:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nessun testo rilevato nella foto dell'atto. Assicurati che l'immagine sia leggibile."
        )

    # 2. Convertiamo il testo OCR in un vettore di embedding
    vettore_query = genera_embedding(testo_estratto)

    # 3. Cerchiamo i 3 documenti più simili nell'archivio
    tutti_i_documenti = db.query(Document).all()
    simili = cerca_documenti_simili(vettore_query, tutti_i_documenti, limite=3, query_testo=testo_estratto)

    risultati = []
    for doc, score in simili:
        risultati.append({
            "documento": map_db_to_schema(doc),
            "punteggio_similarita": round(min(score, 0.99), 3),
            "spiegazione_ia": None
        })

    return {
        "testo_estratto_ocr": testo_estratto[:400] + "...",  # Anteprima per il frontend (non il testo completo)
        "corrispondenze": risultati
    }


@router.get("/{document_id}/recommendations")
def get_document_recommendations(document_id: str, db: Session = Depends(get_db)):
    """
    Suggerisce gli atti semanticamente correlati a quello selezionato.
    Usa lo stesso embedding del documento per trovare i 5 più simili nell'archivio
    (escludendo il documento stesso).

    Utile per "potresti essere interessato anche a..." nella vista dettaglio.
    """
    db_doc = db.query(Document).filter(Document.id == document_id).first()
    if not db_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento non trovato."
        )

    # Se il documento non ha ancora un embedding, non possiamo fare raccomandazioni
    if not db_doc.embedding:
        return []

    vettore_documento = json.loads(db_doc.embedding)

    # Escludiamo il documento corrente dalla lista dei candidati
    altri_documenti = db.query(Document).filter(Document.id != document_id).all()
    simili = cerca_documenti_simili(vettore_documento, altri_documenti, limite=5)

    risultati = []
    for doc, score in simili:
        # La spiegazione di correlazione usa i testi di entrambi i documenti
        spiegazione = spiega_similarita_semantica(db_doc, doc, score)
        risultati.append({
            "documento": map_db_to_schema(doc),
            "punteggio_similarita": round(score, 3),
            "spiegazione_ia": spiegazione
        })

    return risultati


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document_by_id(document_id: str, db: Session = Depends(get_db)):
    """Restituisce i dettagli completi di un singolo documento tramite il suo UUID."""
    db_doc = db.query(Document).filter(Document.id == document_id).first()
    if not db_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documento con ID {document_id} non trovato."
        )
    return map_db_to_schema(db_doc)


# =============================================================================
# ENDPOINT PROTETTI — Operazioni Funzionario
# Tutti questi endpoint richiedono un Bearer Token valido nell'header Authorization.
# =============================================================================

@router.post("/recalculate-embeddings")
def recalculate_all_embeddings(db: Session = Depends(get_db), admin_username: str = Depends(get_current_admin)):
    """
    Ricalcola gli embeddings vettoriali di tutti i documenti nel database.
    Utile dopo un aggiornamento della logica di calcolo vettoriale.
    """
    docs = db.query(Document).all()
    count = 0
    for doc in docs:
        testo_per_embedding = f"{doc.nome} {doc.descrizione or ''} {doc.testo_estratto or ''}"
        vettore = genera_embedding(testo_per_embedding)
        doc.embedding = json.dumps(vettore)
        count += 1
    
    db.commit()
    return {"status": "success", "messaggio": f"Ricalcolati gli embeddings per {count} documenti."}


@router.post("/analyze-ocr")
def analyze_document_via_ocr(
    file: UploadFile = File(..., description="Scansione o foto della copertina dell'atto"),
    db: Session = Depends(get_db),
    admin_username: str = Depends(get_current_admin)
):
    """
    Digitalizza un atto tramite OCR e restituisce una bozza precompilata.
    """
    # 1. Carichiamo l'immagine (su Azure Blob in produzione, in locale in sviluppo)
    url_immagine = storage_service.upload_file(file)

    # 2. Estraiamo il testo (Azure AI Document Intelligence o mock locale)
    testo_estratto = ocr_service.estrai_testo(file)

    # Estraiamo i metadati intelligenti con Azure OpenAI
    tipi = [t.nome for t in db.query(Typology).all()]
    uffici = [u.nome for u in db.query(Office).all()]
    firmatari = [f.nome for f in db.query(Firmatario).all()]
    frazioni = [f.nome for f in db.query(Frazione).all()]
    
    metadati_json = estrai_metadati_da_ocr(testo_estratto, tipi, uffici, firmatari, frazioni)
    
    if metadati_json:
        # GPT ha risposto con successo! Usiamo i suoi dati
        nome = metadati_json.get("nome") or f"Rilevato da {file.filename.split('.')[0].replace('_', ' ')}"
        descrizione = metadati_json.get("descrizione") or (testo_estratto if len(testo_estratto) <= 1500 else testo_estratto[:1500] + "...")
        tipologia = metadati_json.get("tipologia") or ("Delibera" if "delibera" in file.filename.lower() else "Atto")
        data = metadati_json.get("data") or "2026-06-01"
        data_scadenza = metadati_json.get("data_scadenza")
        uffici = metadati_json.get("uffici") or []
        firmatari = metadati_json.get("firmatari") or []
        frazioni = metadati_json.get("frazioni") or []
    else:
        # Fallback locale (spaCy) se Azure OpenAI non è configurato o fallisce
        print("Fallback: Utilizzo spaCy per estrazione metadati.")
        uffici, firmatari = elabora_testo_nlp(testo_estratto)
        nome = f"Rilevato da {file.filename.split('.')[0].replace('_', ' ')}"
        descrizione = testo_estratto if len(testo_estratto) <= 1500 else testo_estratto[:1500] + "..."
        tipologia = "Delibera" if "delibera" in file.filename.lower() else "Atto"
        data = "2026-06-01"
        data_scadenza = None
        frazioni = []

    # 4. Calcoliamo l'embedding dal testo estratto (servirà per la ricerca semantica)
    vettore_embedding = genera_embedding(testo_estratto)

    # Restituiamo la bozza precompilata: il funzionario può correggerla prima di salvare
    return {
        "nome": nome,
        "descrizione": descrizione,
        "tipologia": tipologia,
        "data": data,
        "data_scadenza": data_scadenza,
        "uffici": uffici,
        "firmatari": firmatari,
        "frazioni": frazioni,
        "url_immagine": url_immagine,
        "testo_estratto": testo_estratto,
        "embedding": vettore_embedding
    }


def _valida_metadati_stretta(db: Session, tipologia: str, uffici: list, firmatari: list, frazioni: list):
    if tipologia:
        if not db.query(Typology).filter(Typology.nome == tipologia).first():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Tipologia '{tipologia}' non valida o inesistente.")
    for u in (uffici or []):
        if not db.query(Office).filter(Office.nome == u).first():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Ufficio '{u}' non valido o inesistente.")
    for f in (firmatari or []):
        if not db.query(Firmatario).filter(Firmatario.nome == f).first():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Firmatario '{f}' non valido o inesistente.")
    for fr in (frazioni or []):
        if not db.query(Frazione).filter(Frazione.nome == fr).first():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Frazione '{fr}' non valida o inesistente.")

@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document(
    payload: DocumentCreate,
    db: Session = Depends(get_db),
    admin_username: str = Depends(get_current_admin)
):
    """
    Registra manualmente un nuovo documento nell'archivio.
    L'embedding vettoriale viene calcolato automaticamente dal nome e dalla descrizione
    per abilitare la ricerca semantica del documento appena salvato.
    """
    _valida_metadati_stretta(db, payload.tipologia, payload.uffici, payload.firmatari, payload.frazioni)

    # Calcoliamo l'embedding concatenando nome, descrizione e testo OCR
    testo_per_embedding = f"{payload.nome} {payload.descrizione or ''} {payload.testo_estratto or ''}"
    vettore = genera_embedding(testo_per_embedding)

    new_doc = Document(
        nome=payload.nome,
        descrizione=payload.descrizione,
        tipologia=payload.tipologia,
        data=payload.data,
        # Le liste vengono serializzate in JSON per SQLite
        uffici=json.dumps(payload.uffici),
        firmatari=json.dumps(payload.firmatari),
        url_immagine=payload.url_immagine,
        testo_estratto=payload.testo_estratto,
        embedding=json.dumps(vettore),
        data_scadenza=payload.data_scadenza,
        frazioni=json.dumps(payload.frazioni)
    )

    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    audit = AuditLog(
        username=admin_username,
        action="CREATE_DOC",
        target_id=str(new_doc.id),
        details=f"Creato documento: {new_doc.nome}"
    )
    db.add(audit)
    db.commit()

    return map_db_to_schema(new_doc)


def processa_ocr_background(doc_id: str, url_immagine: str, nome: str, descrizione: str):
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            return

        file_name = url_immagine.split("/")[-1]
        file_path = os.path.join("app", "static", "uploads", file_name)
        
        testo_estratto = None
        content = None
        
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                content = f.read()
        elif url_immagine.startswith("http"):
            import httpx
            try:
                resp = httpx.get(url_immagine, timeout=10.0)
                if resp.status_code == 200:
                    content = resp.content
            except Exception as e:
                print(f"Errore download immagine OCR {url_immagine}: {e}")
                
        if content:
            class DummyUploadFile:
                def __init__(self, filename, content):
                    self.filename = filename
                    self.file = io.BytesIO(content)
            dummy_file = DummyUploadFile(file_name, content)
            testo_estratto = ocr_service.estrai_testo(dummy_file)
        else:
            doc.stato_elaborazione = "errore"
            db.commit()
            return

        doc.testo_estratto = testo_estratto
        testo_per_embedding = f"{nome} {descrizione or ''} {testo_estratto or ''}"
        vettore = genera_embedding(testo_per_embedding)
        doc.embedding = json.dumps(vettore)
        doc.stato_elaborazione = "completato"
        db.commit()
    except Exception as e:
        print(f"Errore in OCR background per doc {doc_id}: {e}")
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc:
            doc.stato_elaborazione = "errore"
            db.commit()
    finally:
        db.close()


@router.post("/import-bulk", status_code=status.HTTP_201_CREATED)
def import_bulk_documents(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="File ZIP contenente il CSV/JSON e le immagini"),
    db: Session = Depends(get_db),
    admin_username: str = Depends(get_current_admin)
):
    """
    Importa massivamente atti da un archivio ZIP.
    L'archivio deve contenere un file CSV o JSON e le relative immagini.
    File non supportati vengono ignorati in modo sicuro e l'archivio non viene mantenuto.
    """
    filename = file.filename.lower()
    
    if not filename.endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato non supportato. Carica un archivio .zip contenente i dati e le immagini."
        )

    try:
        # Costanti di sicurezza anti-ZipBomb
        MAX_ZIP_FILES = 1000
        MAX_UNCOMPRESSED_SIZE = 100 * 1024 * 1024  # 100 MB
        
        # Leggiamo lo ZIP in memoria senza salvarlo
        file_bytes = file.file.read()
        zip_buffer = io.BytesIO(file_bytes)
        
        raw_records = []
        extracted_images = {} # mappiamo filename -> url_storage
        
        with zipfile.ZipFile(zip_buffer, "r") as z:
            info_list = z.infolist()
            if len(info_list) > MAX_ZIP_FILES:
                raise HTTPException(status_code=400, detail=f"Troppi file nell'archivio ZIP (max {MAX_ZIP_FILES}).")
            
            total_uncompressed_size = sum(info.file_size for info in info_list)
            if total_uncompressed_size > MAX_UNCOMPRESSED_SIZE:
                raise HTTPException(status_code=400, detail=f"L'archivio ZIP decompresso supera il limite massimo consentito di {MAX_UNCOMPRESSED_SIZE / (1024*1024):.0f}MB.")
                
            # Troviamo il file metadati
            metadata_files = [f for f in z.namelist() if f.lower().endswith(('.json', '.csv')) and not f.startswith('__MACOSX')]
            
            if len(metadata_files) != 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"L'archivio ZIP deve contenere ESATTAMENTE UN file .csv o .json. Trovati: {len(metadata_files)}"
                )
                
            metadata_filename = metadata_files[0]
            
            # Estraiamo solo le immagini supportate
            upload_dir = os.path.join("app", "static", "uploads")
            os.makedirs(upload_dir, exist_ok=True)
            
            for item in z.namelist():
                if item.startswith('__MACOSX') or item.endswith('/'):
                    continue
                    
                ext = os.path.splitext(item)[1].lower()
                if ext in ['.png', '.jpg', '.jpeg', '.webp']:
                    # Estraiamo il file immagine
                    image_data = z.read(item)
                    base_name = os.path.basename(item)
                    if base_name:  # Evita cartelle con estensioni strane
                        class DummyUploadFile:
                            def __init__(self, filename, content):
                                self.filename = filename
                                self.file = io.BytesIO(content)
                        dummy_file = DummyUploadFile(base_name, image_data)
                        
                        # Usiamo lo storage_service in modo da supportare Azure Blob Storage!
                        url_imm = storage_service.upload_file(dummy_file, folder="documents")
                        extracted_images[base_name] = url_imm
            
            # Leggiamo il file metadati
            with z.open(metadata_filename) as meta_f:
                if metadata_filename.lower().endswith(".json"):
                    data_list = json.loads(meta_f.read().decode("utf-8"))
                    if not isinstance(data_list, list):
                        raise ValueError("Il file JSON deve contenere una lista.")
                    raw_records = data_list
                else:
                    raw_content = meta_f.read().decode("utf-8-sig")
                    try:
                        sample = raw_content[:4096]
                        dialect = csv.Sniffer().sniff(sample)
                        sep = dialect.delimiter
                    except:
                        sep = ',' 
                    df = pd.read_csv(io.StringIO(raw_content), sep=sep, engine="c")
                    raw_records = df.to_dict(orient="records")
                    for r in raw_records:
                        for k, v in r.items():
                            if pd.isna(v):
                                r[k] = None

        # Carichiamo le entità esistenti per controllare cosa manca
        existing_uffici = {u.nome for u in db.query(Office).all()}
        existing_tipologie = {t.nome for t in db.query(Typology).all()}
        existing_frazioni = {f.nome for f in db.query(Frazione).all()}
        existing_firmatari = {f.nome for f in db.query(Firmatario).all()}
        
        nuove_entita = {
            "tipologie": set(),
            "uffici": set(),
            "frazioni": set(),
            "firmatari": set()
        }

        imported_count = 0
        docs_for_background = []
        
        for idx, row in enumerate(raw_records):
            try:
                # Normalizziamo il campo "uffici"
                uffici_raw = row.get("uffici", [])
                if isinstance(uffici_raw, str):
                    if uffici_raw.startswith("["):
                        uffici_list = json.loads(uffici_raw)
                    else:
                        uffici_list = [u.strip() for u in uffici_raw.split(",") if u.strip()]
                else:
                    uffici_list = list(uffici_raw) if uffici_raw else []

                # Stessa normalizzazione per "firmatari"
                firmatari_raw = row.get("firmatari", [])
                if isinstance(firmatari_raw, str):
                    if firmatari_raw.startswith("["):
                        firmatari_list = json.loads(firmatari_raw)
                    else:
                        firmatari_list = [f.strip() for f in firmatari_raw.split(",") if f.strip()]
                else:
                    firmatari_list = list(firmatari_raw) if firmatari_raw else []

                # E per "frazioni"
                frazioni_raw = row.get("frazioni", row.get("frazione", []))
                if isinstance(frazioni_raw, str):
                    if frazioni_raw.startswith("["):
                        frazioni_list = json.loads(frazioni_raw)
                    else:
                        frazioni_list = [f.strip() for f in frazioni_raw.split(",") if f.strip()]
                else:
                    frazioni_list = list(frazioni_raw) if frazioni_raw else []

                testo_estratto = row.get("testo_estratto")
                url_immagine = row.get("url_immagine")

                # REQUISITO: Immagini obbligatorie per ogni documento dello zip
                if not url_immagine or pd.isna(url_immagine):
                    raise ValueError("Immagine mancante. Il campo url_immagine è obbligatorio.")
                
                # Prendiamo solo il nome del file ignorando eventuali path vecchi
                img_basename = os.path.basename(str(url_immagine))
                if img_basename not in extracted_images:
                    raise ValueError(f"L'immagine dichiarata '{img_basename}' non è presente nell'archivio ZIP.")

                # Recuperiamo l'URL effettivo ritornato dallo storage_service (locale o Azure)
                url_immagine_rel = extracted_images[img_basename]

                tipologia_val = row.get("tipologia")
                if tipologia_val and tipologia_val not in existing_tipologie:
                    nuove_entita["tipologie"].add(tipologia_val)
                for u in uffici_list:
                    if u not in existing_uffici:
                        nuove_entita["uffici"].add(u)
                for f in firmatari_list:
                    if f not in existing_firmatari:
                        nuove_entita["firmatari"].add(f)
                for f in frazioni_list:
                    if f not in existing_frazioni:
                        nuove_entita["frazioni"].add(f)

                doc_in = DocumentCreate(
                    nome=row.get("nome"),
                    descrizione=row.get("descrizione"),
                    tipologia=tipologia_val,
                    data=row.get("data"),
                    uffici=uffici_list,
                    firmatari=firmatari_list,
                    data_scadenza=row.get("data_scadenza"),
                    frazioni=frazioni_list,
                    url_immagine=str(url_immagine)
                )

                url_immagine_assoluto = f"http://127.0.0.1:8000{url_immagine_rel}" if not url_immagine_rel.startswith("http") else url_immagine_rel

                # Puliamo testo_estratto da eventuali NaN di pandas
                if pd.isna(testo_estratto) or str(testo_estratto).strip().lower() == "nan" or not str(testo_estratto).strip():
                    testo_estratto = None

                # Facciamo l'OCR in background SOLO se il testo estratto non è già presente
                needs_bg_ocr = (testo_estratto is None)
                vettore_json = None
                stato_elaborazione = "in_elaborazione" if needs_bg_ocr else "completato"

                if not needs_bg_ocr:
                    testo_per_embedding = f"{doc_in.nome} {doc_in.descrizione or ''} {testo_estratto or ''}"
                    vettore = genera_embedding(testo_per_embedding)
                    vettore_json = json.dumps(vettore)

                new_doc = Document(
                    nome=doc_in.nome,
                    descrizione=doc_in.descrizione,
                    tipologia=doc_in.tipologia,
                    data=doc_in.data,
                    uffici=json.dumps(doc_in.uffici),
                    firmatari=json.dumps(firmatari_list),
                    url_immagine=url_immagine_rel,
                    testo_estratto=testo_estratto,
                    embedding=vettore_json,
                    data_scadenza=doc_in.data_scadenza,
                    frazioni=json.dumps(frazioni_list),
                    stato_elaborazione=stato_elaborazione
                )

                db.add(new_doc)
                if needs_bg_ocr:
                    docs_for_background.append((new_doc, url_immagine_rel, doc_in.nome, doc_in.descrizione))

                imported_count += 1

            except Exception as e:
                # Saltiamo il record problematico e logghiamo l'errore, senza interrompere
                print(f"Errore all'indice {idx}: {e}")
                continue

        # Facciamo un unico commit alla fine per tutte le righe valide (più efficiente)
        if imported_count > 0:
            audit = AuditLog(
                username=admin_username,
                action="MASS_IMPORT",
                target_id=None,
                details=f"Importazione massiva di {imported_count} documenti da {filename}"
            )
            db.add(audit)
            db.commit()
            
            # Adesso che i documenti sono nel DB con i loro ID, possiamo accodare i task asincroni
            for doc, url_img, n, d in docs_for_background:
                background_tasks.add_task(processa_ocr_background, doc.id, url_img, n, d)

        return {
            "status": "success",
            "messaggio": f"Importati {imported_count} documenti su {len(raw_records)}.",
            "documenti_importati": imported_count,
            "nuove_entita": {k: list(v) for k, v in nuove_entita.items() if v}
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore durante l'importazione: {str(e)}"
        )


class ResolvedEntityPair(BaseModel):
    original: str
    final: str

class BulkResolvePayload(BaseModel):
    resolved: Dict[str, List[ResolvedEntityPair]]
    deleted: Dict[str, List[str]]

@router.post("/bulk-resolve-entities")
def bulk_resolve_entities(
    payload: BulkResolvePayload,
    db: Session = Depends(get_db),
    admin_username: str = Depends(get_current_admin)
):
    """
    Risolve le entità mancanti (rinomina o elimina) in tutti i documenti.
    Viene chiamato dopo un importBulk massivo.
    """
    try:
        docs = db.query(Document).all()
        
        for doc in docs:
            changed = False
            
            # --- Tipologia ---
            if doc.tipologia:
                # Deleted
                if doc.tipologia in payload.deleted.get("tipologie", []):
                    doc.tipologia = "Atto" # Fallback generico
                    changed = True
                else:
                    # Resolved
                    for r in payload.resolved.get("tipologie", []):
                        if doc.tipologia == r.original:
                            doc.tipologia = r.final
                            changed = True

            # Helper per le liste JSON
            def process_list(field_json, deleted_list, resolved_list):
                if not field_json:
                    return field_json, False
                try:
                    items = json.loads(field_json)
                except:
                    return field_json, False
                
                if not isinstance(items, list):
                    return field_json, False
                    
                new_items = []
                list_changed = False
                for item in items:
                    if item in deleted_list:
                        list_changed = True
                        continue
                        
                    is_resolved = False
                    for r in resolved_list:
                        if item == r.original:
                            new_items.append(r.final)
                            list_changed = True
                            is_resolved = True
                            break
                            
                    if not is_resolved:
                        new_items.append(item)
                
                if list_changed:
                    return json.dumps(new_items), True
                return field_json, False

            # --- Uffici ---
            new_uffici, ch_u = process_list(doc.uffici, payload.deleted.get("uffici", []), payload.resolved.get("uffici", []))
            if ch_u:
                doc.uffici = new_uffici
                changed = True
                
            # --- Firmatari ---
            new_firmatari, ch_f = process_list(doc.firmatari, payload.deleted.get("firmatari", []), payload.resolved.get("firmatari", []))
            if ch_f:
                doc.firmatari = new_firmatari
                changed = True
                
            # --- Frazioni ---
            new_frazioni, ch_fr = process_list(doc.frazioni, payload.deleted.get("frazioni", []), payload.resolved.get("frazioni", []))
            if ch_fr:
                doc.frazioni = new_frazioni
                changed = True
                
            if changed:
                # Ricalcoliamo embedding se la tipologia o gli uffici cambiano? 
                # Potrebbe non essere strettamente necessario per un rename minore, ma facciamolo.
                testo_per_embedding = f"{doc.nome} {doc.descrizione or ''} {doc.testo_estratto or ''}"
                vettore = genera_embedding(testo_per_embedding)
                doc.embedding = json.dumps(vettore)
                db.add(doc)
                
        db.commit()
        return {"status": "success", "messaggio": "Documenti aggiornati correttamente."}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore durante l'aggiornamento massivo: {str(e)}"
        )


@router.put("/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: str,
    payload: DocumentCreate,
    db: Session = Depends(get_db),
    admin_username: str = Depends(get_current_admin)
):
    """
    Modifica un documento esistente.
    Ricalcola automaticamente l'embedding dopo la modifica per mantenere
    la coerenza con i nuovi contenuti nella ricerca semantica.
    """
    db_doc = db.query(Document).filter(Document.id == document_id).first()
    if not db_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento non trovato."
        )

    _valida_metadati_stretta(db, payload.tipologia, payload.uffici, payload.firmatari, payload.frazioni)

    # Calcolo del delta delle modifiche
    changes = []
    if db_doc.nome != payload.nome:
        changes.append(f"nome ('{db_doc.nome}' -> '{payload.nome}')")
    if db_doc.descrizione != payload.descrizione:
        changes.append(f"descrizione ('{db_doc.descrizione}' -> '{payload.descrizione}')")
    if db_doc.tipologia != payload.tipologia:
        changes.append(f"tipologia ('{db_doc.tipologia}' -> '{payload.tipologia}')")
    if db_doc.data != payload.data:
        changes.append(f"data ('{db_doc.data}' -> '{payload.data}')")
    if db_doc.data_scadenza != payload.data_scadenza:
        changes.append(f"scadenza ('{db_doc.data_scadenza}' -> '{payload.data_scadenza}')")
    
    try:
        old_uffici = json.loads(db_doc.uffici) if db_doc.uffici else []
    except:
        old_uffici = []
    if set(old_uffici) != set(payload.uffici):
        changes.append("uffici")
        
    try:
        old_firmatari = json.loads(db_doc.firmatari) if db_doc.firmatari else []
    except:
        old_firmatari = []
    if set(old_firmatari) != set(payload.firmatari):
        changes.append("firmatari")
        
    try:
        old_frazioni = json.loads(db_doc.frazioni) if db_doc.frazioni else []
    except:
        old_frazioni = []
    if set(old_frazioni) != set(payload.frazioni):
        changes.append("frazioni")

    # Aggiorniamo tutti i campi con i nuovi valori
    db_doc.nome = payload.nome
    db_doc.descrizione = payload.descrizione
    db_doc.tipologia = payload.tipologia
    db_doc.data = payload.data
    db_doc.uffici = json.dumps(payload.uffici)
    db_doc.firmatari = json.dumps(payload.firmatari)
    db_doc.url_immagine = payload.url_immagine
    db_doc.testo_estratto = payload.testo_estratto
    db_doc.data_scadenza = payload.data_scadenza
    db_doc.frazioni = json.dumps(payload.frazioni)

    # Ricalcoliamo l'embedding con i nuovi testi:
    # senza questo, la ricerca semantica userebbe ancora il vettore del testo precedente
    testo_per_embedding = f"{payload.nome} {payload.descrizione or ''} {payload.testo_estratto or ''}"
    vettore = genera_embedding(testo_per_embedding)
    db_doc.embedding = json.dumps(vettore)

    db.commit()
    db.refresh(db_doc)

    details_str = f"Modificato documento: {db_doc.nome}."
    if changes:
        details_str += " Campi modificati: " + ", ".join(changes)

    audit = AuditLog(
        username=admin_username,
        action="UPDATE_DOC",
        target_id=str(db_doc.id),
        details=details_str
    )
    db.add(audit)
    db.commit()

    return map_db_to_schema(db_doc)


@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    admin_username: str = Depends(get_current_admin)
):
    """Elimina definitivamente un documento dall'archivio."""
    db_doc = db.query(Document).filter(Document.id == document_id).first()
    if not db_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento non trovato."
        )
    db.delete(db_doc)
    db.commit()

    audit = AuditLog(
        username=admin_username,
        action="DELETE_DOC",
        target_id=str(document_id),
        details=f"Eliminato documento: {db_doc.nome}"
    )
    db.add(audit)
    db.commit()


    return {
        "status": "success",
        "messaggio": f"Documento con ID {document_id} eliminato correttamente."
    }

@router.post("/bulk-delete", status_code=status.HTTP_200_OK)
def bulk_delete_documents(
    request: BulkActionRequest,
    db: Session = Depends(get_db),
    admin_username: str = Depends(get_current_admin)
):
    """Elimina massivamente una lista di documenti dall'archivio (Solo Admin)."""
    docs_to_delete = db.query(Document).filter(Document.id.in_(request.ids)).all()
    
    if not docs_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nessun documento trovato corrispondente agli ID forniti."
        )
    
    deleted_count = 0
    for doc in docs_to_delete:
        db.delete(doc)
        deleted_count += 1
        
    db.commit()
    
    audit = AuditLog(
        username=admin_username,
        action="BULK_DELETE",
        target_id=None,
        details=f"Eliminati massivamente {deleted_count} documenti (IDs: {request.ids})"
    )
    db.add(audit)
    db.commit()
    
    return {
        "status": "success",
        "messaggio": f"{deleted_count} documenti eliminati con successo."
    }

@router.post("/export-bulk")
def export_bulk_documents(
    request: BulkActionRequest,
    db: Session = Depends(get_db)
):
    """
    Esporta i documenti selezionati in un file ZIP contenente
    il file dati.json e le relative immagini. Non richiede autenticazione.
    """
    docs = db.query(Document).filter(Document.id.in_(request.ids)).all()
    if not docs:
        raise HTTPException(status_code=404, detail="Nessun documento trovato.")
        
    # Prepariamo la lista di dizionari per il dati.json
    export_data = []
    # Usiamo un dict per mappare basename_immagine -> url_completo
    images_to_download = {}
    
    for doc in docs:
        doc_resp = map_db_to_schema(doc)
        
        # Creiamo un dict compatibile con DocumentCreate + immagine e testo
        doc_dict = {
            "nome": doc_resp.nome,
            "descrizione": doc_resp.descrizione,
            "tipologia": doc_resp.tipologia,
            "data": doc_resp.data.isoformat() if doc_resp.data else None,
            "uffici": doc_resp.uffici,
            "firmatari": doc_resp.firmatari,
            "data_scadenza": doc_resp.data_scadenza.isoformat() if doc_resp.data_scadenza else None,
            "frazioni": doc_resp.frazioni,
            "testo_estratto": doc_resp.testo_estratto
        }
        
        if doc_resp.url_immagine:
            img_basename = doc_resp.url_immagine.split("/")[-1]
            doc_dict["url_immagine"] = img_basename
            images_to_download[img_basename] = doc_resp.url_immagine
        else:
            doc_dict["url_immagine"] = None
            
        export_data.append(doc_dict)
        
    # Creiamo lo ZIP in memoria
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Scriviamo il file JSON o CSV
        if request.format == "csv":
            import pandas as pd
            df = pd.DataFrame(export_data)
            for col in ["uffici", "firmatari", "frazioni"]:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: ",".join(x) if isinstance(x, list) else x)
            # Usiamo sep=';' ed encoding utf-8-sig in modo che Excel (IT) lo apra correttamente
            csv_str = df.to_csv(index=False, sep=";")
            zf.writestr("dati.csv", csv_str.encode('utf-8-sig'))
        else:
            zf.writestr("dati.json", json.dumps(export_data, indent=2, ensure_ascii=False))
        
        # 2. Leggiamo le immagini direttamente dal disco o le scarichiamo da Azure
        import os
        import httpx
        for img_name, img_url in images_to_download.items():
            file_path = os.path.join("app", "static", "uploads", img_name)
            try:
                if os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        zf.writestr(img_name, f.read())
                elif img_url.startswith("http"):
                    resp = httpx.get(img_url, timeout=10.0)
                    if resp.status_code == 200:
                        zf.writestr(img_name, resp.content)
                    else:
                        print(f"Attenzione: impossibile scaricare l'immagine Azure {img_url}")
                else:
                    print(f"Attenzione: immagine {img_name} non trovata (né su disco né su web).")
            except Exception as e:
                print(f"Errore durante l'elaborazione dell'immagine {img_name}: {e}")
                
    zip_buffer.seek(0)
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=esportazione_massiva.zip"}
    )
