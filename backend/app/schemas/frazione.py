from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Schemi Pydantic per le Frazioni Comunali
#
# Struttura identica a Office e Typology: nome + id.
# Le frazioni rappresentano le zone geografiche del territorio comunale
# (es. "Capoluogo (Centro)", "Frazione Marina").
# ---------------------------------------------------------------------------

class FrazioneBase(BaseModel):
    nome: str = Field(..., description="Nome della frazione o zona comunale")

class FrazioneCreate(FrazioneBase):
    pass  # Nessun campo aggiuntivo rispetto alla Base

class FrazioneResponse(FrazioneBase):
    id: int

    class Config:
        from_attributes = True
