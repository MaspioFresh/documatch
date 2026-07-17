import uuid
from sqlalchemy import Column, String, Text, Date
from app.core.database import Base

# ---------------------------------------------------------------------------
# Modello Document — Rappresenta un atto o documento comunale in archivio
#
# È la tabella centrale dell'applicazione. Ogni riga è un atto amministrativo
# (delibera, ordinanza, autorizzazione, ecc.) con tutti i suoi metadati.
# ---------------------------------------------------------------------------
class Document(Base):
    __tablename__ = "documents"

    # UUID come chiave primaria (stesso motivo del modello User: non prevedibile).
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # --- Metadati base dell'atto ---
    # Numero protocollo/documento non più presente
    nome = Column(String(255), nullable=False)       # Titolo/nome dell'atto
    descrizione = Column(Text, nullable=True)         # Sommario o testo completo
    tipologia = Column(String(100), nullable=False)   # Es: "Delibera di Giunta", "Ordinanza Sindacale"
    data = Column(Date, nullable=False)               # Data di emissione dell'atto

    # --- Campi lista salvati come JSON testuale ---
    # SQLite non supporta i tipi array nativi (a differenza di PostgreSQL).
    # La soluzione adottata è serializzare le liste Python come stringhe JSON:
    # es. uffici = '["Ufficio Tecnico", "Ufficio Ambiente"]'
    # Il router si occupa di serializzare al salvataggio e deserializzare alla lettura.
    uffici = Column(Text, nullable=True)      # Lista degli uffici coinvolti nell'atto
    firmatari = Column(Text, nullable=True)   # Lista dei firmatari dell'atto

    # --- Dati prodotti dall'OCR ---
    url_immagine = Column(String(512), nullable=True)   # URL della foto/scansione della copertina
    testo_estratto = Column(Text, nullable=True)         # Testo completo estratto via OCR

    # --- Vettore di embedding per la ricerca semantica ---
    # Il vettore numerico (lista di ~384 float) viene salvato anch'esso come JSON testuale,
    # per lo stesso motivo dei campi lista sopra. Viene generato automaticamente
    # dal servizio NLP al momento del salvataggio del documento.
    # ⚠️ PUNTO CRITICO: in produzione con milioni di documenti si userebbe un
    # vector database dedicato (es. Azure AI Search, Pinecone) per query più efficienti.
    embedding = Column(Text, nullable=True)

    # --- Campi aggiuntivi introdotti dopo la prima versione ---
    # Questi due campi sono stati aggiunti in un secondo momento: per questo
    # in main.py esiste la funzione run_migrations() che li aggiunge alle
    # installazioni esistenti senza perdere i dati già presenti.
    data_scadenza = Column(Date, nullable=True)        # Data di scadenza dell'atto (opzionale)
    frazioni = Column(Text, nullable=True)      # Frazioni o zone comunali (JSON array)
    stato_elaborazione = Column(String(50), default="completato")
