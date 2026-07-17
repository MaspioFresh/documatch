from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Schemi Pydantic per le Tipologie Documentali
#
# Struttura identica a Office e Frazione: nome + id.
# Le tipologie classificano gli atti (es. "Delibera di Giunta", "Ordinanza").
# ---------------------------------------------------------------------------

class TypologyBase(BaseModel):
    nome: str = Field(..., description="Nome della tipologia documentale")

class TypologyCreate(TypologyBase):
    pass  # Nessun campo aggiuntivo rispetto alla Base

class TypologyResponse(TypologyBase):
    id: int

    class Config:
        from_attributes = True
