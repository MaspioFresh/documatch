from typing import List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.document import Document
from app.schemas.document import DocumentResponse
from app.services.nlp import cerca_documenti_simili, genera_embedding
from app.services.generative_ai import rispondi_domanda_rag
from app.routers.documents import map_db_to_schema

# ---------------------------------------------------------------------------
# Router della Chat — Assistente virtuale RAG
# ---------------------------------------------------------------------------
router = APIRouter(
    prefix="/api/v1/chat",
    tags=["Chat"]
)

class ChatRequest(BaseModel):
    message: str
    document_id: Optional[str] = None
    history: List[dict] = []

# Schema della risposta: testo generato dall'AI + lista delle fonti usate
class ChatResponse(BaseModel):
    response: str
    sources: List[DocumentResponse]  # I documenti trovati dalla ricerca semantica


@router.post("/", response_model=ChatResponse)
def ask_chatbot(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Endpoint RAG (Retrieval-Augmented Generation) — il cuore dell'assistente virtuale.

    Il flusso è:
    1. RETRIEVAL: cerca i documenti più pertinenti nel DB tramite embedding semantici
    2. AUGMENTED: inietta il testo dei documenti trovati nel prompt come contesto
    3. GENERATION: Azure OpenAI genera una risposta basata SOLO sul contesto fornito

    Questo approccio evita le "allucinazioni" dell'AI: il modello risponde
    solo con informazioni presenti nei documenti, non inventa nulla.

    ⚠️ PUNTO CRITICO: se Azure OpenAI non è configurato (chiavi mancanti),
    il sistema funziona comunque in modalità "offline" restituendo
    i documenti trovati con un messaggio di fallback. Nessun crash.
    """
    query = request.message

    # 1. Recuperiamo tutti i documenti dall'archivio
    all_docs = db.query(Document).all()
    
    # Se c'è un document_id (chat contestuale), cerchiamo il documento specifico
    context_doc = None
    if request.document_id:
        context_doc = db.query(Document).filter(Document.id == request.document_id).first()

    # 2. Convertiamo la domanda in un vettore numerico (embedding)
    # e troviamo i 3 documenti con il significato più simile alla domanda
    vettore_query = genera_embedding(query)
    simili = cerca_documenti_simili(vettore_query, all_docs, limite=3, query_testo=query)
    top_docs = [doc for doc, _score in simili]
    
    # Inseriamo il context_doc in cima ai top_docs se presente (rimuovendo eventuali duplicati)
    if context_doc:
        top_docs = [d for d in top_docs if d.id != context_doc.id]
        top_docs.insert(0, context_doc)

    # 3. Chiamiamo Azure OpenAI con la cronologia, la domanda + il contesto dei documenti trovati.
    # Se le chiavi Azure non sono configurate, la funzione ritorna None.
    risposta_generata = rispondi_domanda_rag(query, top_docs, request.history)

    # 4. Fallback offline: se Azure OpenAI non risponde, costruiamo un messaggio
    # di cortesia che elenca comunque i documenti trovati
    if not risposta_generata:
        sources_names = [d.nome for d in top_docs]
        if sources_names:
            docs_list_str = ", ".join([f"'{n}'" for n in sources_names])
            risposta_generata = (
                f"Salve! Sono l'Assistente Virtuale del Comune di Documatch (in modalità offline/locale).\n\n"
                f"Ho analizzato l'archivio ed ho individuato {len(sources_names)} documenti pertinenti:\n"
                f"{docs_list_str}.\n\n"
                f"Nota: Le chiavi di Azure OpenAI non sono configurate in questo ambiente per elaborare risposte generative complete, "
                f"ma puoi consultare ciascuno di questi atti direttamente dall'elenco delle fonti qui sotto."
            )
        else:
            risposta_generata = (
                f"Salve! Sono l'Assistente Virtuale del Comune di Documatch (in modalità offline/locale).\n\n"
                f"Non ho trovato atti o documenti pertinenti alla tua domanda (\"{query}\") nel nostro archivio.\n"
                f"Ti consiglio di provare a riformulare la domanda con parole chiave diverse oppure di contattare l'Ufficio Relazioni con il Pubblico (URP)."
            )

    # Convertiamo i modelli DB in schemi Pydantic per la risposta JSON
    sources_schemas = [map_db_to_schema(d) for d in top_docs]

    return ChatResponse(
        response=risposta_generata,
        sources=sources_schemas
    )
