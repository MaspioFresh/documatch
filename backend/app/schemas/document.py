from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Schemi Pydantic per i documenti
#
# Il pattern usato è: Base → Create → Response.
# Questo permette di separare nettamente cosa il client MANDA (input)
# da cosa il server RESTITUISCE (output), senza duplicare i campi comuni.
# ---------------------------------------------------------------------------

# Campi condivisi tra input e output: sono quelli che il client conosce
# e che il server gestisce in entrambe le direzioni.
class DocumentBase(BaseModel):

    nome: str = Field(..., description="Nome dell'atto amministrativo")
    descrizione: Optional[str] = Field(None, description="Descrizione testuale o sommario dell'atto")
    tipologia: str = Field(..., description="Tipologia (es. Delibera, Autorizzazione, Piano Comunale)")
    data: date = Field(..., description="Data di emissione dell'atto")

    # Uffici e firmatari sono liste di stringhe: Pydantic le valida automaticamente.
    # Il router si occupa di serializzarle in JSON per SQLite e deserializzarle al ritorno.
    uffici: List[str] = Field(default=[], description="Uffici comunali interessati")
    firmatari: List[str] = Field(default=[], description="Firmatari dell'atto")

    url_immagine: Optional[str] = Field(None, description="Link alla foto della copertina")
    testo_estratto: Optional[str] = Field(None, description="Testo completo estratto via OCR")

    # Campi opzionali aggiunti nella seconda versione del progetto
    data_scadenza: Optional[date] = Field(None, description="Data di scadenza dell'atto")
    frazioni: List[str] = Field(default=[], description="Frazioni o zone comunali associate")

# Schema per la creazione: identico alla Base perché non servono campi aggiuntivi.
# "pass" non è un errore: è obbligatorio in Python per avere un corpo di classe valido.
# La classe esiste comunque per distinguere il tipo "input" dal tipo "output" e
# per consentire future estensioni senza toccare la Base.
class DocumentCreate(DocumentBase):
    url_immagine: str = Field(..., min_length=1, description="Link alla foto della copertina (obbligatorio per nuove schede)")

# Schema per la risposta dell'API: aggiunge i campi generati dal server
# (l'id viene assegnato dal DB, l'embedding calcolato dal servizio NLP).
class DocumentResponse(DocumentBase):
    id: str                                # UUID assegnato automaticamente alla creazione
    url_immagine: Optional[str] = None
    testo_estratto: Optional[str] = None
    stato_elaborazione: Optional[str] = "completato"

    # L'embedding è il vettore numerico usato per la ricerca semantica.
    # Viene esposto come lista di float per permettere calcoli lato client se necessario.
    # Può essere None se il documento non ha ancora un embedding calcolato.
    embedding: Optional[List[float]] = None

    class Config:
        # from_attributes=True dice a Pydantic di leggere i dati dagli attributi
        # degli oggetti SQLAlchemy (non solo dai dizionari Python).
        # Senza questo, DocumentResponse.model_validate(db_doc) fallirebbe.
        from_attributes = True

class BulkActionRequest(BaseModel):
    ids: List[str] = Field(..., description="Lista degli ID dei documenti su cui operare")
    format: str = Field(default="json", description="Formato in cui esportare i dati (json o csv)")
