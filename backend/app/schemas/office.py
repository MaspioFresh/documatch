from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Schemi Pydantic per gli Uffici Comunali
#
# Pattern Base → Create → Response (identico per Uffici, Tipologie e Frazioni).
# Tutte e tre le entità hanno la stessa struttura: un nome e un id numerico.
# ---------------------------------------------------------------------------

# Campo condiviso: il nome dell'ufficio (es. "Ufficio Tecnico", "URP")
class OfficeBase(BaseModel):
    nome: str = Field(..., description="Nome dell'ufficio comunale")

# Schema di input per la creazione: identico alla Base, "pass" è obbligatorio
# sintatticamente ma la classe serve per avere un tipo distinto.
class OfficeCreate(OfficeBase):
    pass

# Schema di risposta: aggiunge l'id assegnato dal database
class OfficeResponse(OfficeBase):
    id: int

    class Config:
        from_attributes = True  # Permette di costruire lo schema da oggetti SQLAlchemy
