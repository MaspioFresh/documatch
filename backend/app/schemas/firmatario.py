from pydantic import BaseModel, Field

class FirmatarioBase(BaseModel):
    nome: str = Field(..., description="Nome del firmatario (es. Sindaco Mario Rossi)")

class FirmatarioCreate(FirmatarioBase):
    pass

class FirmatarioResponse(FirmatarioBase):
    id: int

    class Config:
        from_attributes = True
